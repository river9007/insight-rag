# Archivo: backend/models.py
import uuid
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector
from database import Base

class SentimentEnum(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)
    product_id = Column(String, index=True)
    product_name = Column(String, nullable=False, default='')

    review_text = Column(Text, nullable=False)
    rating = Column(Integer)
    chunk_index = Column(Integer, nullable=False, default=0)
    review_group_id = Column(String, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    embedding = Column(Vector(384))

    # Campos para VoC Analytics
    sentiment = Column(
        SQLEnum(SentimentEnum, name='review_sentiment', create_type=False),
        nullable=False,
        default=SentimentEnum.neutral
    )
    category = Column(String(100), nullable=True, index=True)
    aspect_tags = Column(ARRAY(Text), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)