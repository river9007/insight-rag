import asyncio
from sqlalchemy import text
from database import engine

async def test_connection():
    print("Iniciando prueba de conexión...")
    try:
        # Intentamos abrir una conexión y ejecutar un comando simple
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            # Si llegamos aquí, la conexión funcionó
            print("✅ ¡Éxito! Conexión establecida con Supabase.")
            print(f"La base de datos respondió: {result.scalar()}")
    except Exception as e:
        print("❌ Uy, hubo un error al conectar:")
        print(e)

if __name__ == "__main__":
    # Ejecutamos la función asíncrona
    asyncio.run(test_connection())