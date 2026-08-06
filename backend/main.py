# Archivo: backend/main.py
import pandas as pd
import io
import re
import uuid
import asyncio
import unicodedata
from reranker import reranker_instance
from typing import List, Optional, Tuple, Dict, Any
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, cast, Date
from pydantic import BaseModel, Field
from database import engine, Base, get_db
import models
from embeddings import get_embedding, get_embeddings_batch
from fastapi.responses import StreamingResponse
from llm import generate_insight, stream_insight, rewrite_query
from langchain_core.messages import HumanMessage, AIMessage

# Verificador de seguridad JWT
from auth import get_current_user

# Procesamiento de documentos
import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from review_parser import parse_reviews, ParsedReview

# Umbrales para fragmentación (chunking)
MAX_REVIEW_CHUNK_CHARS = 800
RESERVED_PART_LABEL_CHARS = 20
MIN_BODY_CHUNK_SIZE = 200

_HEADER_PATTERN = re.compile(
    r"^(Producto: .+?\.) Reseña(?: \(parte \d+/\d+\))?: ",
    re.DOTALL,
)


def _split_header_body(review_text: str) -> tuple[str, str]:
    match = _HEADER_PATTERN.match(review_text)
    if match:
        return match.group(1), review_text[match.end():]
    return "", review_text


def build_context_text(reviews: List[models.Review]) -> str:
    """
    Consolida los fragmentos recuperados utilizando límites semánticos planos.

    El nombre y el ID del producto vienen de las columnas product_name /
    product_id (no se reconstruyen a partir del texto almacenado) — antes
    se descartaba el header embebido en review_text y el LLM se quedaba
    sin ninguna forma de saber el nombre legible del producto.
    """
    if not reviews:
        return "--- INICIO OPINIONES CUALITATIVAS ---\nNo se encontraron reseñas.\n--- FIN OPINIONES CUALITATIVAS ---"

    groups: dict[str, dict] = {}
    order: list[str] = []

    for r in reviews:
        gid = r.review_group_id
        if gid not in groups:
            groups[gid] = {
                "rating": r.rating,
                "product_id": r.product_id,
                "product_name": r.product_name,
                "chunks": [],
            }
            order.append(gid)
        groups[gid]["chunks"].append((r.chunk_index, r.review_text))

    lines = []
    lines.append("--- INICIO OPINIONES CUALITATIVAS ---")
    lines.append("Advertencia: Usa esta sección SOLO para leer el texto (los pros y contras de los productos). NO utilices esta sección para calcular cuál producto es mejor.")

    for gid in order:
        data = groups[gid]
        chunks_sorted = sorted(data["chunks"], key=lambda c: c[0])

        bodies = []
        for _, text in chunks_sorted:
            # Descartamos el header embebido en el texto almacenado (nombre
            # e ID ya vienen de las columnas, no hace falta reconstruirlos
            # con regex), pero sí necesitamos quitar el prefijo redundante
            # del cuerpo para no repetirlo dentro de las comillas.
            _, body = _split_header_body(text)
            bodies.append(body.strip())

        combined_body = " ".join(bodies)
        lines.append(f"[{data['product_id']} - {data['product_name']}]: \"{combined_body}\"")

    lines.append("--- FIN OPINIONES CUALITATIVAS ---\n")

    return "\n".join(lines)


def repair_excel_corrupted_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detecta si Excel envolvió toda la línea del CSV entre comillas dobles,
    colocando todo el contenido en la primera columna y dejando el resto como NaN.
    Reconstruye el DataFrame en memoria preservando la veracidad de los datos.
    """
    if df.shape[1] > 1:
        first_col = df.columns[0]
        other_cols = df.columns[1:]

        if df[other_cols].isna().all(axis=1).sum() >= (len(df) * 0.5):
            reconstructed_lines = [",".join(str(c) for c in df.columns)]
            for val in df[first_col].dropna():
                reconstructed_lines.append(str(val))

            try:
                fixed_df = pd.read_csv(io.StringIO("\n".join(reconstructed_lines)))
                if fixed_df.shape[1] >= 3:
                    return fixed_df
            except Exception:
                pass
    return df


def parse_dataframe_reviews(df: pd.DataFrame) -> Tuple[List[ParsedReview], List[Dict[str, Any]]]:
    """
    Convierte un DataFrame de pandas (CSV/Excel) en objetos ParsedReview.
    Garantiza la veracidad e integridad de los datos rechazando filas corruptas
    sin alterar ni inventar valores.
    """
    df = repair_excel_corrupted_df(df)

    def normalize_col_name(name):
        s = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('utf-8')
        return re.sub(r'[^a-z0-9]', '', s.lower())

    norm_map = {normalize_col_name(c): c for c in df.columns}

    id_col = None
    rating_col = None
    text_col = None
    name_col = None

    for norm, orig in norm_map.items():
        if norm in ['productid', 'idproducto', 'iddeproducto', 'id', 'productoid', 'codigo']:
            id_col = orig
        elif norm in ['rating', 'puntuacion', 'calificacion', 'estrellas', 'score', 'nota']:
            rating_col = orig
        elif norm in ['text', 'texto', 'resena', 'comment', 'review', 'opinion']:
            text_col = orig
        elif norm in ['productname', 'nombreproducto', 'nombre', 'product', 'producto']:
            name_col = orig

    if not (id_col and rating_col and text_col):
        raise HTTPException(
            status_code=422,
            detail=(
                f"No se detectaron las columnas requeridas. "
                f"Columnas detectadas: {list(df.columns)}. "
                f"Se requiere al menos: ID de producto, Rating y Texto/Reseña."
            )
        )

    parsed_reviews: List[ParsedReview] = []
    skipped_rows: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        row_num = idx + 2

        text_val = str(row[text_col]).strip() if pd.notna(row[text_col]) else ""
        if not text_val:
            skipped_rows.append({"fila": row_num, "motivo": "El texto de la reseña está vacío."})
            continue

        raw_rating = row[rating_col]
        try:
            rating_val = float(raw_rating)
            if not rating_val.is_integer():
                skipped_rows.append({"fila": row_num, "motivo": f"El rating '{raw_rating}' debe ser un número entero."})
                continue

            rating_int = int(rating_val)
            if not (1 <= rating_int <= 5):
                skipped_rows.append({"fila": row_num, "motivo": f"El rating {rating_int} está fuera del rango válido (1 a 5)."})
                continue
        except (ValueError, TypeError):
            skipped_rows.append({"fila": row_num, "motivo": f"El rating '{raw_rating}' no es un valor numérico válido."})
            continue

        raw_id = str(row[id_col]).strip() if pd.notna(row[id_col]) else ""
        if not raw_id:
            skipped_rows.append({"fila": row_num, "motivo": "Falta el identificador del producto."})
            continue

        p_name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""

        match = re.match(r"^(?P<id>[^\(]+)\s*(?:\(\s*(?P<name>[^)]+)\s*\))?", raw_id)
        if match:
            p_id = match.group("id").strip()
            extracted_name = match.group("name")
            if extracted_name and not p_name:
                p_name = extracted_name.strip()
        else:
            p_id = raw_id

        if not p_name:
            p_name = p_id

        parsed_reviews.append(
            ParsedReview(
                product_id=p_id,
                product_name=p_name,
                rating=rating_int,
                text=text_val
            )
        )

    return parsed_reviews, skipped_rows


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
    version="1.2.5",
    lifespan=lifespan
)

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
    limit: int = Field(default=10, ge=1, le=20, description="Número máximo de fragmentos a recuperar")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Pregunta para el modelo LLM basándose en el contexto")
    history: List[Message] = Field(default=[], description="Historial de la conversación")
    limit: int = Field(default=10, ge=1, le=20, description="Número de documentos a extraer")
    product_id: Optional[str] = Field(default=None, description="ID del producto para filtrar contexto")

@app.get("/")
async def root():
    return {"status": "ok", "message": "InsightRAG Backend corriendo"}


async def get_global_metrics_context(db: AsyncSession, user_id: uuid.UUID, product_id: Optional[str] = None) -> str:
    """
    Inyecta métricas globales calculadas con SQL puro sobre TODAS las
    reseñas del usuario (no limitadas por la búsqueda semántica).

    Las listas de "5 mejores" y "5 peores" se pre-calculan aquí, en Python,
    en vez de pedirle al LLM que filtre/reordene la tabla completa por su
    cuenta. En pruebas reales, un modelo de 8B parámetros (llama-3.1-8b-
    instant) cometía errores de orden al hacer esa selección él mismo
    (ej. colocaba un producto con promedio 3.5 al final de una lista
    descendente, o incluía el producto con MEJOR promedio dentro de la
    lista de "peores"). Al entregarle las dos listas ya armadas, su única
    tarea es copiar la correcta según la pregunta — una tarea mucho más
    simple y confiable que ordenar/filtrar.
    """
    base_filter = [models.Review.chunk_index == 0, models.Review.user_id == user_id]
    if product_id:
        base_filter.append(models.Review.product_id == product_id)

    stmt = (
        select(
            models.Review.product_id,
            func.max(models.Review.product_name).label("product_name"),
            func.avg(models.Review.rating).label("promedio"),
            func.count().label("total")
        )
        .where(*base_filter)
        .group_by(models.Review.product_id)
        .order_by(func.avg(models.Review.rating).desc(), func.count().desc())
    )
    result = await db.execute(stmt)

    ranking_rows = [
        (row.product_id, row.product_name, round(float(row.promedio), 2), row.total)
        for row in result
    ]

    if not ranking_rows:
        return ""

    def format_ranking(rows: list[tuple[str, str, float, int]]) -> str:
        return "\n".join(
            f"{i}. {pid} ({pname}) | Promedio: {avg}/5 | Total Reseñas: {tot}"
            for i, (pid, pname, avg, tot) in enumerate(rows, 1)
        )

    tabla_completa = format_ranking(ranking_rows)
    top_mejores = format_ranking(ranking_rows[:5])
    top_peores = format_ranking(list(reversed(ranking_rows[-5:])))

    return (
        "--- INICIO DATOS CUANTITATIVOS ---\n"
        "Rol: Analista de Datos Senior.\n"
        "Tabla de Métricas Globales completa (ordenada de mejor a peor):\n" +
        tabla_completa +
        "\n\nLISTA PRE-CALCULADA — TOP 5 MEJORES (usar textualmente y sin cambios si preguntan por el MEJOR/TOP):\n" +
        top_mejores +
        "\n\nLISTA PRE-CALCULADA — TOP 5 PEORES (usar textualmente y sin cambios si preguntan por el PEOR):\n" +
        top_peores +
        "\n\nREGLA DE FORMATO ESTRICTA - Cuando te pregunten por el 'mejor' o 'peor' producto, DEBES estructurar tu respuesta EXACTAMENTE así:\n"
        "1. Empieza con una frase natural respondiendo la pregunta (ej. 'Basado en las métricas consolidadas, el mejor producto es...' o 'el producto con la calificación más baja es...'). Jamás menciones que estás leyendo unas instrucciones.\n"
        "2. Si el producto destacado (el mejor o el peor, según lo que se haya preguntado) tiene muy pocas reseñas (ej. 1 o 2), añade una breve advertencia analítica indicando que la muestra es pequeña.\n"
        "3. Copia OBLIGATORIAMENTE la lista pre-calculada correspondiente (LISTA PRE-CALCULADA — TOP 5 MEJORES o LISTA PRE-CALCULADA — TOP 5 PEORES, según lo que se haya preguntado) EXACTAMENTE tal como se te dio, en el mismo orden, sin reordenar, sin omitir elementos y sin inventar ninguno nuevo. NUNCA construyas esa lista tú mismo a partir de la tabla completa — usa siempre la lista pre-calculada ya provista.\n"
        "--- FIN DATOS CUANTITATIVOS ---\n\n"
    )


async def get_relevant_reviews(
    query: str, 
    limit: int, 
    db: AsyncSession,
    user_id: uuid.UUID,
    product_id: Optional[str] = None
) -> List[models.Review]:
    query_vector = await asyncio.to_thread(get_embedding, query)
    
    stmt = select(models.Review).where(models.Review.user_id == user_id)
    
    if product_id:
        stmt = stmt.where(models.Review.product_id == product_id)
        
    # Corrección: escala dinámicamente según el 'limit' solicitado por el usuario
    candidate_limit = max(limit * 2, 10)
    stmt = (
        stmt.order_by(models.Review.embedding.cosine_distance(query_vector))
        .limit(candidate_limit)
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    # Re-ranking sobre la muestra real recuperada
    reranked_reviews = await reranker_instance.rerank(
        query=query, 
        reviews=candidates, 
        top_k=min(limit, len(candidates))
    )

    return reranked_reviews


# 1. ENDPOINT: Búsqueda Semántica
@app.post("/search")
async def search_reviews(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user.get("sub"))
    reviews = await get_relevant_reviews(request.query, request.limit, db, user_uuid, request.product_id)

    return {
        "query": request.query,
        "results": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "product_name": r.product_name,
                "rating": r.rating,
                "review_group_id": r.review_group_id,
                "chunk_index": r.chunk_index,
                "text": r.review_text
            }
            for r in reviews
        ]
    }

# 2. ENDPOINT: Análisis Completo
@app.post("/analyze")
async def analyze_reviews(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user.get("sub"))
    
    role_mapping = {"user": HumanMessage, "assistant": AIMessage}
    langchain_history = [
        role_mapping[msg.role](content=msg.content) 
        for msg in request.history 
        if msg.role in role_mapping
    ]

    search_query = await rewrite_query(request.query, langchain_history) if langchain_history else request.query
    
    reviews = await get_relevant_reviews(search_query, request.limit, db, user_uuid, request.product_id)
    global_metrics = await get_global_metrics_context(db, user_uuid, request.product_id)
    
    context_text = global_metrics + build_context_text(reviews)

    insight = await generate_insight(context=context_text, question=request.query, chat_history=langchain_history)

    seen_groups = set()
    unique_sources = []
    for r in reviews:
        if r.review_group_id not in seen_groups:
            unique_sources.append({"id": r.id, "rating": r.rating})
            seen_groups.add(r.review_group_id)

    return {
        "query": request.query,
        "insight": insight,
        "sources": unique_sources
    }

# 3. ENDPOINT: Streaming de Análisis
@app.post("/analyze/stream")
async def analyze_reviews_stream(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user.get("sub"))
    
    role_mapping = {"user": HumanMessage, "assistant": AIMessage}
    langchain_history = [
        role_mapping[msg.role](content=msg.content) 
        for msg in request.history 
        if msg.role in role_mapping
    ]

    search_query = await rewrite_query(request.query, langchain_history) if langchain_history else request.query
    
    reviews = await get_relevant_reviews(search_query, request.limit, db, user_uuid, request.product_id)
    global_metrics = await get_global_metrics_context(db, user_uuid, request.product_id)

    context_text = global_metrics + build_context_text(reviews)

    seen_groups = set()
    sources_data = []
    
    for r in reviews:
        if r.review_group_id not in seen_groups:
            sources_data.append({
                "id": str(r.id),
                "product_id": r.product_id, 
                "rating": r.rating,
                "text_preview": r.review_text[:100] + "..." if len(r.review_text) > 100 else r.review_text
            })
            seen_groups.add(r.review_group_id)

    async def event_generator():
        async for chunk in stream_insight(
            context=context_text, 
            question=request.query, 
            chat_history=langchain_history,
            sources=sources_data
        ):
            yield chunk

    # CONFIGURACIÓN PROFESIONAL DE CABECERAS PARA STREAMING HTTP
    return StreamingResponse(
        event_generator(), 
        media_type="text/plain", 
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff"
        }
    )

# 4. ENDPOINT: Métricas Agregadas
@app.get("/metrics")
async def get_metrics(
    product_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user.get("sub"))

    base_filter = [
        models.Review.chunk_index == 0,
        models.Review.user_id == user_uuid
    ]
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
        .where(
            models.Review.chunk_index == 0,
            models.Review.user_id == user_uuid
        )
        .distinct()
        .order_by(models.Review.product_id)
    )
    products_result = await db.execute(products_stmt)
    available_products = [row.product_id for row in products_result]

    # --- NUEVO: CÁLCULO DE SERIE TEMPORAL (Evolución) ---
    timeseries_stmt = (
        select(
            cast(models.Review.created_at, Date).label("fecha"),
            func.avg(models.Review.rating).label("promedio_diario"),
            func.count().label("cantidad")
        )
        .where(*base_filter)
        .group_by(cast(models.Review.created_at, Date))
        .order_by(cast(models.Review.created_at, Date))
    )
    
    timeseries_result = await db.execute(timeseries_stmt)
    
    timeseries = [
        {
            "fecha": row.fecha.isoformat() if row.fecha else "Desconocida",
            "promedio": round(float(row.promedio_diario), 1) if row.promedio_diario else 0.0,
            "cantidad": row.cantidad
        }
        for row in timeseries_result
    ]
    # --- FIN NUEVO ---

    return {
        "total_resenas": total,
        "promedio": promedio,
        "alertas": alertas,
        "distribution": distribution,
        "available_products": available_products,
        "filtered_by": product_id,
        "timeseries": timeseries, # 👈 Nueva propiedad expuesta a la API
    }

# 5. ENDPOINT: Ingesta de Documentos
@app.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="El archivo excede el tamaño máximo permitido (10MB).")

        parsed_reviews: List[ParsedReview] = []
        skipped_rows: List[Dict[str, Any]] = []

        if filename.endswith('.csv'):
            df = None
            for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=None, engine='python')
                    break
                except Exception:
                    continue

            if df is None:
                raise HTTPException(
                    status_code=400, 
                    detail="No se pudo interpretar la codificación ni el separador del archivo CSV."
                )

            parsed_reviews, skipped_rows = parse_dataframe_reviews(df)

        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
            parsed_reviews, skipped_rows = parse_dataframe_reviews(df)

        elif filename.endswith('.pdf'):
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            raw_text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
            parsed_reviews = parse_reviews(raw_text)

        elif filename.endswith('.txt'):
            raw_text = content.decode('utf-8', errors='ignore')
            parsed_reviews = parse_reviews(raw_text)

        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Debe ser CSV, Excel, PDF o TXT.")

        if not parsed_reviews:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No se procesó ninguna reseña válida. "
                    "Verifica que el archivo contenga datos veraces y cumpla con la estructura requerida."
                )
            )

        # chunks_to_insert: (product_id, product_name, rating, texto, chunk_index, review_group_id)
        chunks_to_insert: list[tuple[str, str, int, str, int, str]] = []

        for review in parsed_reviews:
            group_id = str(uuid.uuid4())
            base_header = f"Producto: {review.product_name} ({review.product_id}). Reseña"
            simple_text = f"{base_header}: {review.text}"

            if len(simple_text) <= MAX_REVIEW_CHUNK_CHARS:
                chunks_to_insert.append((review.product_id, review.product_name, review.rating, simple_text, 0, group_id))
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
                chunks_to_insert.append((review.product_id, review.product_name, review.rating, enriched_sub_chunk, idx, group_id))

        raw_user_id = user.get("sub")
        user_uuid = uuid.UUID(raw_user_id)

        # Procesamiento en LOTE (Batch) de embeddings.
        # Ejecuta una única llamada C++ optimizada a nivel de motor ONNX.
        texts_to_embed = [item[3] for item in chunks_to_insert]
        vectors = await asyncio.to_thread(get_embeddings_batch, texts_to_embed)

        new_reviews = [
            models.Review(
                user_id=user_uuid,
                product_id=product_id,
                product_name=product_name,
                rating=rating,
                review_text=text,
                embedding=vector,
                chunk_index=chunk_index,
                review_group_id=group_id,
            )
            for (product_id, product_name, rating, text, chunk_index, group_id), vector in zip(chunks_to_insert, vectors)
        ]

        db.add_all(new_reviews)
        await db.commit()

        return {
            "status": "success",
            "message": f"Archivo '{file.filename}' procesado correctamente.",
            "resenas_importadas": len(parsed_reviews),
            "filas_omitidas": len(skipped_rows),
            "detalle_filas_omitidas": skipped_rows,
            "chunks_creados": len(new_reviews)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en la ingesta: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 6. ENDPOINTS DE GESTIÓN DE DOCUMENTOS

@app.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    raw_user_id = user.get("sub")
    user_uuid = uuid.UUID(raw_user_id)

    stmt = select(models.Review).where(
        models.Review.user_id == user_uuid,
        models.Review.chunk_index == 0
    ).order_by(models.Review.id.desc())

    result = await db.execute(stmt)
    reviews = result.scalars().all()

    documents = [
        {
            "review_group_id": r.review_group_id,
            "product_id": r.product_id,
            "product_name": r.product_name,
            "rating": r.rating,
            "text_preview": r.review_text[:120] + "..." if len(r.review_text) > 120 else r.review_text,
        }
        for r in reviews
    ]

    return {"count": len(documents), "documents": documents}


@app.delete("/documents/all")
async def delete_all_documents(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    raw_user_id = user.get("sub")
    user_uuid = uuid.UUID(raw_user_id)

    stmt = delete(models.Review).where(models.Review.user_id == user_uuid)
    result = await db.execute(stmt)
    await db.commit()

    return {
        "status": "success",
        "message": "Todos los documentos han sido eliminados de tu base de conocimientos.",
        "rows_deleted": result.rowcount
    }


@app.delete("/documents/{review_group_id}")
async def delete_document_group(
    review_group_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    raw_user_id = user.get("sub")
    user_uuid = uuid.UUID(raw_user_id)

    stmt = delete(models.Review).where(
        models.Review.user_id == user_uuid,
        models.Review.review_group_id == review_group_id
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404, 
            detail="El documento no existe o no tienes permisos para eliminarlo."
        )

    return {
        "status": "success",
        "message": f"Reseña o documento {review_group_id} eliminado correctamente.",
        "rows_deleted": result.rowcount
    }