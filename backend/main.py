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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from review_parser import parse_reviews

# Umbral para sub-dividir una reseña individual demasiado larga.
# Por encima de esto, un solo embedding pierde precisión semántica.
MAX_REVIEW_CHUNK_CHARS = 800

review_sub_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_REVIEW_CHUNK_CHARS,
    chunk_overlap=100,
)

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
    query_vector = await asyncio.to_thread(get_embedding, request.query)

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
    query_vector = await asyncio.to_thread(get_embedding, request.query)

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
    query_vector = await asyncio.to_thread(get_embedding, request.query)

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

        # Intentamos extraer reseñas estructuradas (product_id + rating reales).
        # Este sistema está diseñado específicamente para reseñas de productos:
        # si el documento no contiene ningún bloque reconocible, se rechaza
        # en lugar de ingerirlo con datos incompletos que corromperían las
        # métricas de rating más adelante.
        parsed_reviews = parse_reviews(extracted_text)

        if not parsed_reviews:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No se encontró ninguna reseña con el formato esperado. "
                    "Cada bloque debe seguir el patrón: "
                    "'ID de Producto: PROD-XXXX (Nombre) Rating: N Reseña: texto...'"
                )
            )

        # Construimos los fragmentos finales a insertar: (product_id, rating, texto)
        chunks_to_insert: list[tuple[str, int, str]] = []

        for review in parsed_reviews:
            # Reinsertamos el nombre del producto dentro del texto porque el
            # regex lo extrae del encabezado — sin esto, el LLM perdería esa
            # referencia al analizar el fragmento de forma aislada.
            enriched_text = f"Producto: {review.product_name} ({review.product_id}). Reseña: {review.text}"

            if len(enriched_text) > MAX_REVIEW_CHUNK_CHARS:
                sub_texts = review_sub_splitter.split_text(enriched_text)
                for sub_text in sub_texts:
                    chunks_to_insert.append((review.product_id, review.rating, sub_text))
            else:
                chunks_to_insert.append((review.product_id, review.rating, enriched_text))

        new_reviews = []
        for product_id, rating, text in chunks_to_insert:
            vector = await asyncio.to_thread(get_embedding, text)

            review_entry = models.Review(
                product_id=product_id,
                rating=rating,
                review_text=text,
                embedding=vector
            )
            new_reviews.append(review_entry)

        db.add_all(new_reviews)
        await db.commit()

        return {
            "status": "success",
            "message": f"Archivo '{file.filename}' procesado exitosamente por el usuario {user.get('email')}.",
            "resenas_detectadas": len(parsed_reviews),
            "chunks_creados": len(new_reviews)
        }

    except HTTPException:
        # Re-lanzamos tal cual las HTTPException ya construidas (400/422)
        # para no perder el mensaje específico bajo el except genérico de abajo.
        raise
    except Exception as e:
        print(f"Error en la ingesta: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))