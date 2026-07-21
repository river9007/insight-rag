# Archivo: backend/database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("La variable DATABASE_URL no está configurada en el archivo .env")

# Crear el motor asíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    prepared_statement_cache_size=0,  # Nivel SQLAlchemy: deshabilita nombres de sentencias preparadas
    connect_args={
        "statement_cache_size": 0     # Nivel asyncpg: deshabilita la caché interna del driver
    }
)

# Fábrica de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False, 
    expire_on_commit=False
)

# Clase base para nuestros modelos
Base = declarative_base()

# Dependencia para inyectar la sesión en los endpoints de FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session