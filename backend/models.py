# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    product_id = Column(String, index=True)

    # Nombre legible del producto (ej. "Monitor UltraWide Curve 38\"").
    # Antes solo existía embebido dentro de review_text; se añade como
    # columna propia para que el contexto del LLM pueda mostrarlo sin
    # depender de parsear el texto almacenado.
    product_name = Column(String, nullable=False, default='')

    review_text = Column(Text, nullable=False)
    rating = Column(Integer)
    chunk_index = Column(Integer, nullable=False, default=0)
    review_group_id = Column(String, nullable=False, index=True)
    embedding = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False) 