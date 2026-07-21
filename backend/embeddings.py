# Archivo: backend/embeddings.py
from fastembed import TextEmbedding

# Fastembed soporta nativamente el mismo modelo que usábamos antes
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Cargando modelo FastEmbed: {MODEL_NAME}...")

# Iniciamos el modelo de forma ligera
model = TextEmbedding(model_name=MODEL_NAME)
print("Modelo cargado correctamente.")

def get_embedding(text: str) -> list[float]:
    """
    Convierte un texto en un vector usando FastEmbed.
    """
    # model.embed() devuelve un iterador/generador, lo convertimos a lista
    # y tomamos el primer (y único) vector de la consulta.
    vector_array = list(model.embed([text]))[0]
    return vector_array.tolist()