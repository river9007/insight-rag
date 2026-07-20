# Archivo: backend/seed_db.py
import asyncio
from database import AsyncSessionLocal
from embeddings import get_embedding
import models

# Una lista con reseñas de diferentes temas para poner a prueba a la IA
mock_reviews = [
    {"product_id": "PROD-002", "rating": 5, "text": "La pantalla OLED es increíble, los colores son súper vivos y los negros perfectos."},
    {"product_id": "PROD-002", "rating": 1, "text": "Pésimo servicio al cliente. El paquete llegó tarde, abollado y no me quieren hacer el reembolso."},
    {"product_id": "PROD-001", "rating": 5, "text": "La batería es una bestia, me dura casi dos días completos con uso intenso sin pasar por el cargador."},
    {"product_id": "PROD-003", "rating": 3, "text": "El sonido es decente, pero por el precio que pagué esperaba unos graves mucho más potentes."},
    {"product_id": "PROD-004", "rating": 4, "text": "El teclado es muy ergonómico y cómodo para programar, aunque el trackpad se siente un poco pequeño."},
    {"product_id": "PROD-001", "rating": 2, "text": "El portátil se calienta muchísimo cuando juego. Además, la batería se drena en menos de 2 horas si abres algo pesado."},
    {"product_id": "PROD-005", "rating": 5, "text": "El envío fue rapidísimo, lo compré un domingo y el lunes por la mañana ya lo tenía en casa."},
]

async def seed_data():
    print("Iniciando inyección de datos...")
    
    async with AsyncSessionLocal() as session:
        for item in mock_reviews:
            print(f"Procesando reseña: '{item['text'][:30]}...'")
            
            # 1. Convertimos el texto a vector usando tu modelo local
            vector = get_embedding(item["text"])
            
            # 2. Preparamos el objeto para la base de datos
            new_review = models.Review(
                product_id=item["product_id"],
                rating=item["rating"],
                review_text=item["text"],
                embedding=vector
            )
            session.add(new_review)
            
        # 3. Hacemos el commit para guardar todo de una vez
        await session.commit()
        print("✅ ¡Todas las reseñas y sus vectores han sido guardados en Supabase!")

if __name__ == "__main__":
    asyncio.run(seed_data())