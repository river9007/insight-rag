# Archivo: backend/embeddings.py
from fastembed import TextEmbedding

# BAAI/bge-small-en-v1.5:
#   - 384 dimensiones exactas (compatible con Vector(384) en Supabase)
#   - Modelo ONNX: ~70MB, sin PyTorch, cabe en Render free tier (512MB RAM)
#   - Alta calidad semántica para tareas de retrieval
#   - Se descarga una vez en build/primer arranque y queda cacheado
_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_embedding(text: str) -> list[float]:
    """
    Devuelve un vector de 384 dimensiones para el texto dado.
    Ejecución completamente local — sin llamadas a APIs externas.
    """
    embeddings = list(_model.embed([text]))
    return embeddings[0].tolist()