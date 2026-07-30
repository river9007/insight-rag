# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(String, index=True)  # Para filtrar reseñas por producto
    review_text = Column(Text, nullable=False)  # El texto original del fragmento
    rating = Column(Integer)  # Calificación (1 a 5)

    # 0 = primer fragmento de una reseña real. 1, 2, 3... = sub-fragmentos
    chunk_index = Column(Integer, nullable=False, default=0)

    # Identifica de forma única CADA reseña real
    review_group_id = Column(String, nullable=False, index=True)

    # Columna vectorial de 384 dimensiones
    embedding = Column(Vector(384))

    # Trazabilidad temporal automática (servidor de BD)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)