# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True) # Para filtrar reseñas por producto
    review_text = Column(Text, nullable=False) # El texto original de la reseña
    rating = Column(Integer) # Calificación (ej. 1 a 5)
    
    # Aquí está la magia: Una columna vectorial de 384 dimensiones
    embedding = Column(Vector(384))