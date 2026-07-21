# Archivo: backend/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware # NUEVO IMPORT
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import engine, Base, get_db
import models
from embeddings import get_embedding
from fastapi.responses import StreamingResponse
# Importaciones limpias de llm.py (sin duplicados)
from llm import generate_insight, stream_insight

# Si get_embedding es síncrona, descomenta la siguiente línea:
# from fastapi.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando aplicación y conectando a la base de datos...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    print("Apagando aplicación...")

app = FastAPI(title="InsightRAG API", lifespan=lifespan)

# NUEVO: Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://insight-rag-ten.vercel.app"  # <-- Tu dominio de Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para validación de peticiones
class SearchRequest(BaseModel):
    query: str
    limit: int = 3

class AnalyzeRequest(BaseModel):
    query: str
    limit: int = 5

@app.get("/")
async def root():
    return {"status": "ok", "message": "InsightRAG Backend corriendo"}

# 1. ENDPOINT: Búsqueda Semántica
@app.post("/search")
async def search_reviews(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    print(f"Buscando reseñas similares a: '{request.query}'")
    
    query_vector = get_embedding(request.query)
    
    stmt = (
        select(models.Review)
        .order_by(models.Review.embedding.cosine_distance(query_vector))
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

# 2. ENDPOINT: Análisis Completo (Bloqueante/JSON)
@app.post("/analyze")
async def analyze_reviews(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    print(f"Analizando contexto para: '{request.query}'")
    
    query_vector = get_embedding(request.query)
    stmt = (
        select(models.Review)
        .order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(request.limit)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    context_text = "\n".join([
        f"- Rating: {r.rating}/5. Reseña: {r.review_text}" 
        for r in reviews
    ])
    
    insight = await generate_insight(context=context_text, question=request.query)
    
    return {
        "query": request.query,
        "insight": insight,
        "sources": [{"id": r.id, "rating": r.rating} for r in reviews]
    }

# 3. ENDPOINT: Streaming de Análisis (Token a Token)
@app.post("/analyze/stream")
async def analyze_reviews_stream(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    print(f"Streaming de análisis para: '{request.query}'")
    
    # 1. Recuperación de contexto de la BD
    query_vector = get_embedding(request.query)
    stmt = (
        select(models.Review)
        .order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(request.limit)
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    # 2. Formateo de Contexto para el LLM
    context_text = "\n".join([
        f"- Rating: {r.rating}/5. Reseña: {r.review_text}" 
        for r in reviews
    ])
    
    # 3. Función generadora que consume el 'async for' de tu llm.py
    async def event_generator():
        async for chunk in stream_insight(context=context_text, question=request.query):
            yield str(chunk)

    # 4. Devolvemos la respuesta manteniendo la conexión HTTP abierta
    return StreamingResponse(event_generator(), media_type="text/plain")