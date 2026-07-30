import io
import re
import uuid
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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

# Umbral objetivo para el tamaño final de cada fragmento (encabezado + cuerpo).
# Por encima de esto, un solo embedding pierde precisión semántica.
MAX_REVIEW_CHUNK_CHARS = 800

# Reserva fija para la etiqueta "(parte X/Y): " que se añade a los sub-fragmentos
# de una reseña larga. 20 caracteres cubre holgadamente hasta 999 partes.
RESERVED_PART_LABEL_CHARS = 20

# Piso mínimo de espacio útil para el CUERPO de cada sub-fragmento.
MIN_BODY_CHUNK_SIZE = 200

# Extrae "Producto: X (Y)." del inicio de un fragmento enriquecido, dejando
# aparte el cuerpo real de la reseña. Se usa para reconstruir una reseña
# completa a partir de varios fragmentos sin repetir el encabezado.
_HEADER_PATTERN = re.compile(
    r"^(Producto: .+?\.) Reseña(?: \(parte \d+/\d+\))?: ",
    re.DOTALL,
)

def _split_header_body(review_text: str) -> tuple[str, str]:
    match = _HEADER_PATTERN.match(review_text)
    if match:
        return match.group(1), review_text[match.end():]
    # Fallback defensivo: no debería ocurrir con datos generados por
    # nuestro propio ingest, pero evita un crash si el formato no matchea.
    return "", review_text


def build_context_text(reviews: List[models.Review]) -> str:
    """
    Consolida los fragmentos recuperados en UNA sola línea de contexto por
    reseña real, agrupando por review_group_id (NO por product_id — dos
    reseñas distintas del mismo producto tienen review_group_id distintos,
    así que nunca se fusionan entre sí).

    Por qué existe esta función: en pruebas reales, cuando una reseña larga
    llegaba dividida en 3 fragmentos, el contexto anterior generaba 3 líneas
    "- Rating: 5/5." repetidas. El modelo (Llama 3.1 8B) interpretaba ese
    patrón visual repetido como si fueran 3 reseñas distintas, incluso con
    una instrucción explícita en el prompt pidiéndole lo contrario. La
    solución robusta es resolver la consolidación aquí, en código
    determinista, en vez de depender de que el LLM siga correctamente una
    instrucción textual en cada respuesta.
    """
    if not reviews:
        return "No se encontraron reseñas en la base de datos."

    # ------------------------------------------------------------------
    # NUEVO: Cálculo de extremos en código para garantizar empates exactos
    # ------------------------------------------------------------------
    max_rating = max(r.rating for r in reviews)
    min_rating = min(r.rating for r in reviews)
    
    # Extraemos los IDs únicos de todos los productos que empatan
    mejores_ids = set([r.product_id for r in reviews if r.rating == max_rating])
    peores_ids = set([r.product_id for r in reviews if r.rating == min_rating])
    
    resumen_calculado = (
        "[DATOS PRE-CALCULADOS EXACTOS POR EL SISTEMA]\n"
        f"- Mejor valoración presente: {max_rating}/5 (Corresponde a: {', '.join(mejores_ids)})\n"
        f"- Peor valoración presente: {min_rating}/5 (Corresponde a: {', '.join(peores_ids)})\n"
        "[FIN DATOS PRE-CALCULADOS]\n\n"
    )

    groups: dict[str, dict] = {}
    order: list[str] = []

    for r in reviews:
        gid = r.review_group_id
        if gid not in groups:
            groups[gid] = {"rating": r.rating, "chunks": []}
            order.append(gid)
        groups[gid]["chunks"].append((r.chunk_index, r.review_text))

    lines = []
    for gid in order:
        data = groups[gid]
        # Ordenamos por chunk_index real (no por el orden de recuperación
        # por similitud, que puede venir desordenado) para reconstruir la
        # reseña en su secuencia original.
        chunks_sorted = sorted(data["chunks"], key=lambda c: c[0])

        product_header = ""
        bodies = []
        for _, text in chunks_sorted:
            header, body = _split_header_body(text)
            if not product_header:
                product_header = header
            bodies.append(body)

        combined_body = " ".join(bodies)
        prefix = f"{product_header} " if product_header else ""
        lines.append(f"- Rating: {data['rating']}/5. {prefix}Reseña: {combined_body}")

    # Retornamos el resumen matemático exacto + las reseñas agrupadas limpias
    return resumen_calculado + "\n".join(lines)


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
    limit: int = Field(default=10, ge=1, le=20, description="Número máximo de fragmentos a recuperar (mínimo 1, máximo 20)")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="La pregunta que quieres que Llama 3 responda basándose en el contexto")
    history: List[Message] = Field(default=[], description="Historial de la conversación para mantener el contexto")
    limit: int = Field(default=10, ge=1, le=20, description="Número de documentos a extraer de la base vectorial (mínimo 1, máximo 20)")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

@app.get("/")
async def root():
    return {"status": "ok", "message": "InsightRAG Backend corriendo"}

# --- FUNCIÓN AUXILIAR DRY PARA LA BÚSQUEDA ---
async def get_relevant_reviews(
    query: str, 
    limit: int, 
    db: AsyncSession, 
    product_id: Optional[str] = None
) -> List[models.Review]:
    query_vector = await asyncio.to_thread(get_embedding, query)
    stmt = select(models.Review)
    
    if product_id:
        stmt = stmt.where(models.Review.product_id == product_id)
        
    stmt = (
        stmt.order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# 1. ENDPOINT: Búsqueda Semántica (Protegido)
@app.post("/search")
async def search_reviews(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    print(f"Usuario {user.get('sub')} buscando: '{request.query}'")
    
    reviews = await get_relevant_reviews(request.query, request.limit, db, request.product_id)

    return {
        "query": request.query,
        "results": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "rating": r.rating,
                "review_group_id": r.review_group_id,
                "chunk_index": r.chunk_index,
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
    reviews = await get_relevant_reviews(request.query, request.limit, db, request.product_id)

    context_text = build_context_text(reviews)

    role_mapping = {
        "user": HumanMessage,
        "assistant": AIMessage
    }
    langchain_history = [
        role_mapping[msg.role](content=msg.content) 
        for msg in request.history 
        if msg.role in role_mapping
    ]

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
    reviews = await get_relevant_reviews(request.query, request.limit, db, request.product_id)

    context_text = build_context_text(reviews)

    role_mapping = {
        "user": HumanMessage,
        "assistant": AIMessage
    }
    langchain_history = [
        role_mapping[msg.role](content=msg.content) 
        for msg in request.history 
        if msg.role in role_mapping
    ]

    async def event_generator():
        async for chunk in stream_insight(context=context_text, question=request.query, chat_history=langchain_history):
            yield str(chunk)

    return StreamingResponse(event_generator(), media_type="text/plain")

# 4. ENDPOINT: Métricas Agregadas (Protegido)
@app.get("/metrics")
async def get_metrics(
    product_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Devuelve estadísticas agregadas sobre las reseñas ingeridas.

    IMPORTANTE: todas las agregaciones filtran por chunk_index == 0.
    chunk_index se reinicia en 0 para CADA reseña real (independientemente
    de su review_group_id o product_id), así que contar filas con
    chunk_index == 0 ya cuenta correctamente cada reseña real una sola vez,
    incluso si el mismo product_id tuviera varias reseñas distintas.
    """
    base_filter = [models.Review.chunk_index == 0]
    if product_id:
        base_filter.append(models.Review.product_id == product_id)

    total_stmt = select(func.count()).select_from(models.Review).where(*base_filter)
    total = (await db.execute(total_stmt)).scalar() or 0

    avg_stmt = select(func.avg(models.Review.rating)).where(*base_filter)
    avg_raw = (await db.execute(avg_stmt)).scalar()
    promedio = round(float(avg_raw), 1) if avg_raw is not None else 0.0

    alertas_stmt = select(func.count()).select_from(models.Review).where(
        *base_filter, models.Review.rating <= 2
    )
    alertas = (await db.execute(alertas_stmt)).scalar() or 0

    dist_stmt = (
        select(models.Review.rating, func.count().label("cantidad"))
        .where(*base_filter)
        .group_by(models.Review.rating)
    )
    dist_result = await db.execute(dist_stmt)
    dist_raw = {row.rating: row.cantidad for row in dist_result}

    distribution = [
        {"rating": r, "cantidad": dist_raw.get(r, 0)}
        for r in [5, 4, 3, 2, 1]
    ]

    products_stmt = (
        select(models.Review.product_id)
        .where(models.Review.chunk_index == 0)
        .distinct()
        .order_by(models.Review.product_id)
    )
    products_result = await db.execute(products_stmt)
    available_products = [row.product_id for row in products_result]

    return {
        "total_resenas": total,
        "promedio": promedio,
        "alertas": alertas,
        "distribution": distribution,
        "available_products": available_products,
        "filtered_by": product_id,
    }

# 5. ENDPOINT: Ingesta de Documentos PDF (Protegido)
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

        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="El PDF es demasiado grande. Máximo 10MB permitido.")

        pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))

        extracted_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="El PDF está vacío o no se pudo extraer el texto.")

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

        # Construimos los fragmentos finales: (product_id, rating, texto,
        # chunk_index, review_group_id). Cada reseña PARSEADA (no cada
        # fragmento) recibe un review_group_id único (UUID) que comparten
        # todos sus sub-fragmentos — esto es lo que permite distinguir dos
        # reseñas distintas del mismo product_id al reconstruir contexto.
        chunks_to_insert: list[tuple[str, int, str, int, str]] = []

        for review in parsed_reviews:
            group_id = str(uuid.uuid4())
            base_header = f"Producto: {review.product_name} ({review.product_id}). Reseña"
            simple_text = f"{base_header}: {review.text}"

            if len(simple_text) <= MAX_REVIEW_CHUNK_CHARS:
                chunks_to_insert.append((review.product_id, review.rating, simple_text, 0, group_id))
                continue

            available_body_size = max(
                MAX_REVIEW_CHUNK_CHARS - len(base_header) - RESERVED_PART_LABEL_CHARS,
                MIN_BODY_CHUNK_SIZE,
            )

            local_splitter = RecursiveCharacterTextSplitter(
                chunk_size=available_body_size,
                chunk_overlap=min(100, available_body_size // 4),
            )
            sub_texts = local_splitter.split_text(review.text)
            total_parts = len(sub_texts)

            for idx, sub_text in enumerate(sub_texts):
                enriched_sub_chunk = f"{base_header} (parte {idx + 1}/{total_parts}): {sub_text}"
                chunks_to_insert.append((review.product_id, review.rating, enriched_sub_chunk, idx, group_id))

        # Procesamiento secuencial de embeddings (una llamada a la vez).
        new_reviews = []
        for product_id, rating, text, chunk_index, group_id in chunks_to_insert:
            vector = await asyncio.to_thread(get_embedding, text)

            review_entry = models.Review(
                product_id=product_id,
                rating=rating,
                review_text=text,
                embedding=vector,
                chunk_index=chunk_index,
                review_group_id=group_id,
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
        raise
    except Exception as e:
        print(f"Error en la ingesta: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))