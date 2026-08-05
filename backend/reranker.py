import asyncio
import logging
import os
from typing import List
import models

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "onnx_reranker_fp32")

# Verificación segura de librerías ONNX
try:
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer
    OPTIMUM_AVAILABLE = True
except ImportError:
    OPTIMUM_AVAILABLE = False


class RAGReRanker:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.enabled = False
        self.tokenizer = None
        self.model = None

        if not OPTIMUM_AVAILABLE:
            logger.warning("⚠️ 'optimum' no instalado. Reranker ejecutará en modo passthrough.")
            return

        if not os.path.exists(model_path):
            logger.warning(f"⚠️ No se encontró '{model_path}'. Reranker en modo passthrough.")
            return

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = ORTModelForSequenceClassification.from_pretrained(
                model_path,
                file_name="model.onnx"
            )
            self.enabled = True
            logger.info("✅ ReRanker ONNX cargado exitosamente.")
        except Exception as e:
            logger.error(f"⚠️ Error al cargar ONNX: {e}. Activando modo passthrough.")

    def _sync_rerank(self, query: str, reviews: List[models.Review], top_k: int) -> List[models.Review]:
        if not reviews:
            return []

        # Passthrough directo de la búsqueda vectorial si ONNX no está disponible
        if not self.enabled:
            return reviews[:top_k]

        try:
            queries = [query] * len(reviews)
            texts = [r.review_text for r in reviews]

            inputs = self.tokenizer(
                queries,
                texts,
                padding=True,
                truncation=True,
                max_length=64,
                return_tensors="np"
            )

            outputs = self.model(**inputs)
            raw_scores = outputs.logits.squeeze(-1).tolist()
            scores = [raw_scores] if isinstance(raw_scores, float) else raw_scores

            scored_reviews = sorted(zip(reviews, scores), key=lambda item: item[1], reverse=True)
            return [review for review, score in scored_reviews[:top_k]]
        except Exception as e:
            logger.error(f"Error durante re-ranking: {e}. Retornando resultados vectoriales.")
            return reviews[:top_k]

    async def rerank(self, query: str, reviews: List[models.Review], top_k: int) -> List[models.Review]:
        if not self.enabled:
            return reviews[:top_k]
        return await asyncio.to_thread(self._sync_rerank, query, reviews, top_k)


# Instancia global segura
reranker_instance = RAGReRanker()