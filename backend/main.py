import io
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from database import engine, Base, get_db
import models
from embeddings import get_embedding
from fastapi.responses import StreamingResponse
from llm import generate_insight, stream_insight
from langchain_core.messages import HumanMessage, AIMessage

# Importamos el verificador de seguridad JWT
from auth import get_current_user

# Importaciones para procesamiento de PDFs y Chunking
import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando aplicación y conectando a la base de datos...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    print("Apagando aplicación...")

app = FastAPI(
    title="InsightRAG 🚀",
    description="API de búsqueda semántica y análisis de reseñas de productos usando pgvector y Llama 3.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://insight-rag-ten.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class SearchRequest(BaseModel):
    query: str = Field(..., description="Texto o concepto a buscar en la base de datos de conocimiento")
    limit: int = Field(default=3, description="Número máximo de fragmentos a recuperar")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="La pregunta que quieres que Llama 3 responda basándose en el contexto")
    history: List[Message] = Field(default=[], description="Historial de la conversación para mantener el contexto")
    limit: int = Field(default=5, description="Número de documentos a extraer de la base vectorial")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

@app.get("/")
async def root():
    return {"status": "ok", "message": "InsightRAG Backend corriendo"}

# 1. ENDPOINT: Búsqueda Semántica (Protegido)
@app.post("/search")
async def search_reviews(
    request: SearchRequest, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    print(f"Usuario {user.get('sub')} buscando: '{request.query}'")
    query_vector = get_embedding(request.query)
    
    # 🛡️ MEJORA 3: Filtrado dinámico
    stmt = select(models.Review)
    
    if request.product_id:
        stmt = stmt.where(models.Review.product_id == request.product_id)
        
    stmt = (
        stmt.order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(request.limit)
    )
    
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    return {
        "query": request.query,
        "results": [
            {
                "id": r.id, 
                "product_id": r.product_id, 
                "rating": r.rating, 
                "text": r.review_text
            }
            for r in reviews
        ]
    }

# 2. ENDPOINT: Análisis Completo (Protegido)
@app.post("/analyze")
async def analyze_reviews(
    request: AnalyzeRequest, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    query_vector = get_embedding(request.query)
    
    # 🛡️ MEJORA 3: Filtrado dinámico
    stmt = select(models.Review)
    
    if request.product_id:
        stmt = stmt.where(models.Review.product_id == request.product_id)
        
    stmt = (
        stmt.order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(request.limit)
    )
    
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    context_text = "\n".join([
        f"- Rating: {r.rating}/5. Reseña: {r.review_text}" 
        for r in reviews
    ])
    
    langchain_history = []
    for msg in request.history:
        if msg.role == "user":
            langchain_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_history.append(AIMessage(content=msg.content))
    
    insight = await generate_insight(context=context_text, question=request.query, chat_history=langchain_history)
    
    return {
        "query": request.query,
        "insight": insight,
        "sources": [{"id": r.id, "rating": r.rating} for r in reviews]
    }

# 3. ENDPOINT: Streaming de Análisis (Protegido)
@app.post("/analyze/stream")
async def analyze_reviews_stream(
    request: AnalyzeRequest, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    query_vector = get_embedding(request.query)
    
    # 🛡️ MEJORA 3: Filtrado dinámico (Context Fencing en Base de Datos)
    stmt = select(models.Review)
    
    if request.product_id:
        stmt = stmt.where(models.Review.product_id == request.product_id)
        
    stmt = (
        stmt.order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(request.limit)
    )
    
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    context_text = "\n".join([
        f"- Rating: {r.rating}/5. Reseña: {r.review_text}" 
        for r in reviews
    ])
    
    langchain_history = []
    for msg in request.history:
        if msg.role == "user":
            langchain_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_history.append(AIMessage(content=msg.content))
    
    async def event_generator():
        async for chunk in stream_insight(context=context_text, question=request.query, chat_history=langchain_history):
            yield str(chunk)

    return StreamingResponse(event_generator(), media_type="text/plain")

# 4. ENDPOINT: Ingesta de Documentos PDF (Protegido)
@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Por ahora, solo soportamos archivos PDF.")

    try:
        file_content = await file.read()
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
        
        extracted_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="El PDF está vacío o no se pudo extraer el texto.")

        doc = Document(
            page_content=extracted_text, 
            metadata={"source": file.filename}
        )
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents([doc])
        
        new_reviews = []
        for chunk in chunks:
            vector = await asyncio.to_thread(get_embedding, chunk.page_content)
            
            review_entry = models.Review(
                product_id=file.filename,
                rating=5,
                review_text=chunk.page_content,
                embedding=vector
            )
            new_reviews.append(review_entry)
        
        db.add_all(new_reviews)
        await db.commit()
        
        return {
            "status": "success", 
            "message": f"Archivo '{file.filename}' procesado exitosamente por el usuario {user.get('email')}.",
            "chunks_creados": len(chunks)
        }
        
    except Exception as e:
        print(f"Error en la ingesta: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))