# Archivo: backend/ingest.py
import asyncio
from database import AsyncSessionLocal
from models import Review
from embeddings import get_embedding

# Dataset de prueba: Reseñas de unos auriculares inalámbricos (Product ID: PROD-001)
MOCK_REVIEWS = [
    {"product_id": "PROD-001", "rating": 5, "text": "El sonido es increíble y la cancelación de ruido funciona perfecto en la oficina."},
    {"product_id": "PROD-001", "rating": 2, "text": "La batería no dura las 8 horas que prometen, a lo mucho llega a 4. Muy decepcionado."},
    {"product_id": "PROD-001", "rating": 4, "text": "Son cómodos, pero el micrófono en llamadas se escucha un poco lejos."},
    {"product_id": "PROD-001", "rating": 1, "text": "Dejaron de cargar al mes de uso. El conector USB-C está defectuoso por diseño."},
    {"product_id": "PROD-001", "rating": 5, "text": "Excelente relación calidad-precio. Los bajos son muy potentes y se conectan rápido."}
]

async def ingest_data():
    print("Iniciando proceso de ingesta (ETL)...")
    
    # Abrimos la sesión con la BD
    async with AsyncSessionLocal() as session:
        for item in MOCK_REVIEWS:
            print(f"Vectorizando reseña: '{item['text'][:30]}...'")
            
            # 1. Transformación: Convertimos el texto a matemáticas
            vector = get_embedding(item["text"])
            
            # 2. Mapeo: Creamos el registro usando nuestro modelo de SQLAlchemy
            new_review = Review(
                product_id=item["product_id"],
                review_text=item["text"],
                rating=item["rating"],
                embedding=vector
            )
            
            # 3. Añadimos el registro a la transacción actual
            session.add(new_review)
        
        # 4. Carga: Guardamos permanentemente todos los cambios en la BD
        await session.commit()
        print("¡Ingesta completada! Reseñas guardadas en Supabase.")

if __name__ == "__main__":
    # Como nuestra función es async, necesitamos asyncio para ejecutarla directamente
    asyncio.run(ingest_data())