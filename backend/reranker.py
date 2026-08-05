import asyncio
import os
import time
from typing import List
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer
import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "onnx_reranker_fp32")


class RAGReRanker:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ No se encontró el modelo en '{model_path}'.")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Cargar el modelo ONNX FP32 optimizado
        self.model = ORTModelForSequenceClassification.from_pretrained(
            model_path,
            file_name="model.onnx"
        )

    def _sync_rerank(self, query: str, reviews: List[models.Review], top_k: int) -> List[models.Review]:
        if not reviews:
            return []

        queries = [query] * len(reviews)
        texts = [r.review_text for r in reviews]

        # ---------------------------------------------------------------------
        # ⚙️ PARÁMETRO DE RENDIMIENTO: max_length
        # - 64 tokens: Ultra rápido en CPU (~900 ms para 5 candidatos). Ideal desarrollo local.
        # - 128 tokens: Mayor contexto cualitativo, más lento en CPU (~1.8s). Usar si hay GPU.
        # ---------------------------------------------------------------------
        inputs = self.tokenizer(
            queries,
            texts,
            padding=True,
            truncation=True,
            max_length=64,
            return_tensors="np"
        )

        # Ejecución de inferencia en ONNX Runtime
        outputs = self.model(**inputs)
        raw_scores = outputs.logits.squeeze(-1).tolist()

        # Normalizar scores si se procesó un solo candidato (float en lugar de list)
        scores = [raw_scores] if isinstance(raw_scores, float) else raw_scores

        # Reordenar las reseñas por puntaje de mayor a menor
        scored_reviews = sorted(zip(reviews, scores), key=lambda item: item[1], reverse=True)

        # Devolver solo los top_k seleccionados
        return [review for review, score in scored_reviews[:top_k]]

    async def rerank(self, query: str, reviews: List[models.Review], top_k: int) -> List[models.Review]:
        """
        Ejecuta el reordenamiento de forma asíncrona enviando el cómputo pesado
        de la CPU a un hilo secundario para no bloquear el event loop de FastAPI.
        """
        return await asyncio.to_thread(self._sync_rerank, query, reviews, top_k)


# Instancia singleton global para evitar recargar el modelo en memoria en cada request
reranker_instance = RAGReRanker()