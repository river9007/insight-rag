# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True)  # Para filtrar reseñas por producto
    review_text = Column(Text, nullable=False)  # El texto original de la reseña
    rating = Column(Integer)  # Calificación (ej. 1 a 5)

    # 0 = primer fragmento de una reseña real. 1, 2, 3... = sub-fragmentos
    # cuando la reseña era demasiado larga y se dividió (ver review_parser.py).
    # Las métricas agregadas (/metrics) solo cuentan filas con chunk_index == 0
    # para no inflar el conteo de reseñas reales cuando una se sub-divide.
    chunk_index = Column(Integer, nullable=False, default=0)

    # Columna vectorial de 384 dimensiones
    embedding = Column(Vector(384))