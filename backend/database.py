# Archivo: backend/database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable DATABASE_URL no está configurada en el archivo .env")

# 🛡️ PROTECCIÓN CRÍTICA: Asegurar que SQLAlchemy use el driver asíncrono
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Determinar si estamos en desarrollo para los logs de consultas SQL
is_development = os.getenv("ENVIRONMENT") == "development"

# Crear el motor asíncrono optimizado para Supabase
engine = create_async_engine(
    DATABASE_URL,
    echo=is_development,
    pool_pre_ping=True,  # Verifica validez de conexiones antes de ejecutarlas
    pool_recycle=1800,   # Recicla conexiones inactivas tras 30 min
    connect_args={
        "statement_cache_size": 0,  # Desactiva preparado de sentencias para PgBouncer (Supabase)
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
    """Generador de sesiones asíncronas para inyección de dependencias en FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session