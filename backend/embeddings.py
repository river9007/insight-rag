import os
import google.generativeai as genai

# 1. Configurar el cliente usando GEMINI_API_KEY (la que pondremos en Render)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_embedding(text: str) -> list[float]:
    """
    Toma un texto y devuelve su vector de embedding usando Gemini de forma ligera.
    """
    try:
        # 2. Llamada a la API de embeddings de Google
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document", 
        )
        return result['embedding']
    except Exception as e:
        print(f"Error al generar embedding con Gemini: {e}")
        return []