# Archivo: backend/database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable DATABASE_URL no está configurada en el archivo .env")

# 🛡️ PROTECCIÓN CRÍTICA: Asegurar que SQLAlchemy use el driver asíncrono
# Supabase da la URL como 'postgresql://' o 'postgres://', pero create_async_engine exige 'postgresql+asyncpg://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Determinar si estamos en desarrollo para los logs
is_development = os.getenv("ENVIRONMENT") == "development"

# Crear el motor asíncrono blindado
engine = create_async_engine(
    DATABASE_URL,
    echo=is_development, # Falso en producción para no saturar los logs
    future=True,
    connect_args={
        "statement_cache_size": 0, # Vital para el pooler de Supabase (puerto 6543)
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
        try:
            yield session
        finally:
            await session.close() # Buena práctica: asegurar el cierre de sesión siempre