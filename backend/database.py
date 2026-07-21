# Archivo: backend/database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable DATABASE_URL no está configurada en el archivo .env")

# Crear el motor asíncrono con la caché de prepared statements desactivada
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    prepared_statement_cache_size=0,  # <-- Apaga la caché en SQLAlchemy
    connect_args={
        "statement_cache_size": 0     # <-- Apaga la caché en asyncpg (vital para Supabase Pooler)
    }
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session