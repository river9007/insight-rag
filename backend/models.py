# Archivo: backend/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID # 🛡️ Importar UUID de PostgreSQL
from pgvector.sqlalchemy import Vector
from database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    
    # 🛡️ CORRECCIÓN: Definido como UUID nativo para alinearse con Supabase auth.users
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True) 
    
    product_id = Column(String, index=True)
    review_text = Column(Text, nullable=False)
    rating = Column(Integer)
    chunk_index = Column(Integer, nullable=False, default=0)
    review_group_id = Column(String, nullable=False, index=True)
    embedding = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)