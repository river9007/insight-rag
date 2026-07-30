# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True)  # Para filtrar reseñas por producto
    review_text = Column(Text, nullable=False)  # El texto original del fragmento
    rating = Column(Integer)  # Calificación (ej. 1 a 5)

    # 0 = primer fragmento de una reseña real. 1, 2, 3... = sub-fragmentos
    # cuando la reseña era demasiado larga y se dividió. Las métricas
    # agregadas (/metrics) solo cuentan filas con chunk_index == 0 para no
    # inflar el conteo de reseñas reales cuando una se sub-divide.
    chunk_index = Column(Integer, nullable=False, default=0)

    # Identifica de forma única CADA reseña real (no cada fragmento ni cada
    # producto). Todos los fragmentos de una misma reseña comparten el mismo
    # review_group_id — esto permite distinguir correctamente dos reseñas
    # DISTINTAS del mismo product_id (ej. dos clientes reseñando el mismo
    # producto), algo que agrupar solo por product_id fusionaría por error.
    review_group_id = Column(String, nullable=False, index=True)

    # Columna vectorial de 384 dimensiones
    embedding = Column(Vector(384))