# Archivo: backend/embeddings.py
from sentence_transformers import SentenceTransformer

# Cargamos el modelo. 
# La primera vez que ejecutes esto, descargará los pesos del modelo desde HuggingFace (unos ~80MB).
MODEL_NAME = "all-MiniLM-L6-v2"
print(f"Cargando modelo de embeddings: {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)
print("Modelo cargado correctamente.")

def get_embedding(text: str) -> list[float]:
    """
    Toma un texto y devuelve su representación vectorial (384 dimensiones).
    """
    # encode() devuelve un array de numpy, lo convertimos a lista de Python puro
    # porque pgvector de SQLAlchemy espera una lista estándar.
    vector = model.encode(text)
    return vector.tolist()