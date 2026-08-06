# Archivo: backend/ingest.py
import asyncio
import uuid
from database import AsyncSessionLocal
from models import Review, SentimentEnum
from embeddings import get_embedding

# Dataset de prueba expandido con metadatos de producto y categoría
MOCK_REVIEWS = [
    {
        "product_id": "PROD-001",
        "product_name": "Auriculares Inalámbricos Noise-Canceling",
        "rating": 5,
        "text": "El sonido es increíble y la cancelación de ruido funciona perfecto en la oficina.",
        "category": "Calidad de Sonido",
        "aspect_tags": ["cancelación de ruido", "audio", "oficina"]
    },
    {
        "product_id": "PROD-001",
        "product_name": "Auriculares Inalámbricos Noise-Canceling",
        "rating": 2,
        "text": "La batería no dura las 8 horas que prometen, a lo mucho llega a 4. Muy decepcionado.",
        "category": "Batería",
        "aspect_tags": ["duración", "batería", "autonomía"]
    },
    {
        "product_id": "PROD-001",
        "product_name": "Auriculares Inalámbricos Noise-Canceling",
        "rating": 4,
        "text": "Son cómodos, pero el micrófono en llamadas se escucha un poco lejos.",
        "category": "Micrófono y Llamadas",
        "aspect_tags": ["comodidad", "micrófono", "llamadas"]
    },
    {
        "product_id": "PROD-001",
        "product_name": "Auriculares Inalámbricos Noise-Canceling",
        "rating": 1,
        "text": "Dejaron de cargar al mes de uso. El conector USB-C está defectuoso por diseño.",
        "category": "Hardware y Carga",
        "aspect_tags": ["usb-c", "defectuoso", "carga"]
    },
    {
        "product_id": "PROD-001",
        "product_name": "Auriculares Inalámbricos Noise-Canceling",
        "rating": 5,
        "text": "Excelente relación calidad-precio. Los bajos son muy potentes y se conectan rápido.",
        "category": "Calidad de Sonido",
        "aspect_tags": ["bajos", "conectividad", "precio"]
    }
]

def derive_sentiment(rating: int) -> SentimentEnum:
    """Clasificación heurística rápida basada en el rating."""
    if rating >= 4:
        return SentimentEnum.positive
    elif rating == 3:
        return SentimentEnum.neutral
    else:
        return SentimentEnum.negative

async def ingest_data():
    print("Iniciando proceso de ingesta (ETL) enriquecido...")
    
    async with AsyncSessionLocal() as session:
        for item in MOCK_REVIEWS:
            print(f"Vectorizando y etiquetando reseña: '{item['text'][:30]}...'")
            
            # 1. Transformación: Generar vector
            vector = get_embedding(item["text"])
            
            # 2. Inferencia / Etiquetado de sentimiento
            sentiment_value = derive_sentiment(item["rating"])
            
            # 3. Mapeo al modelo SQLAlchemy
            new_review = Review(
                user_id=uuid.uuid4(),
                product_id=item["product_id"],
                product_name=item["product_name"],
                review_text=item["text"],
                rating=item["rating"],
                embedding=vector,
                sentiment=sentiment_value,
                category=item.get("category", "General"),
                aspect_tags=item.get("aspect_tags", []),
                review_group_id=str(uuid.uuid4()),
                chunk_index=0
            )
            
            session.add(new_review)
        
        await session.commit()
        print("¡Ingesta completada! Reseñas con metadatos analíticos guardadas en Supabase.")

if __name__ == "__main__":
    asyncio.run(ingest_data())