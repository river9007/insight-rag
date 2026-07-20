# Archivo: backend/embeddings.py
from fastembed import TextEmbedding

# Usamos el mismo modelo pero desde el catálogo optimizado de fastembed
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
print(f"Cargando modelo de embeddings ligero: {MODEL_NAME}...")

# Inicializa el modelo usando ONNX Runtime (consume muy poca memoria RAM)
model = TextEmbedding(model_name=MODEL_NAME)
print("Modelo ligero cargado correctamente.")

def get_embedding(text: str) -> list[float]:
    """
    Toma un texto y devuelve su representación vectorial (384 dimensiones).
    """
    # fastembed procesa en lotes y devuelve un iterador; extraemos el primer vector
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()