import logging
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Importamos la instancia configurada de Groq desde tu llm.py
from llm import llm

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 1. Esquema de Salida Estructurada (Pydantic v2)
# ------------------------------------------------------------------
class VoCMetadata(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Sentimiento general de la reseña: positive, neutral o negative."
    )
    category: Literal[
        "Calidad de Producto",
        "Rendimiento/Batería",
        "Precio/Valor",
        "Atención al Cliente",
        "Envío/Empaque",
        "Usabilidad/Diseño",
        "General"
    ] = Field(
        description="Categoría principal de negocio a la que pertenece la reseña."
    )
    aspect_tags: List[str] = Field(
        default_factory=list,
        description="Lista de 1 a 3 etiquetas cortas en español representando aspectos específicos (ej: ['batería', 'sobrecalentamiento'])."
    )


# ------------------------------------------------------------------
# 2. Prompt y Chain de Extracción
# ------------------------------------------------------------------
parser = JsonOutputParser(pydantic_object=VoCMetadata)

VOC_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Eres un analista experto en Voz del Cliente (VoC).\n"
        "Tu tarea es analizar el texto de una reseña de producto y clasificarla de forma precisa.\n\n"
        "Debes responder EXCLUSIVAMENTE en formato JSON cumpliendo este esquema:\n"
        "{format_instructions}"
    ),
    (
        "human",
        "Analiza la siguiente reseña:\n\n\"{review_text}\""
    )
])

voc_chain = VOC_PROMPT | llm | parser


# ------------------------------------------------------------------
# 3. Función Principal de Extracción (Resiliente)
# ------------------------------------------------------------------
async def extract_voc_metadata_async(review_text: str) -> VoCMetadata:
    """
    Analiza una reseña individual y extrae sentimiento, categoría y etiquetas.
    Retorna valores por defecto seguros en caso de texto vacío o error en el LLM.
    """
    if not review_text or not review_text.strip():
        return VoCMetadata(
            sentiment="neutral",
            category="General",
            aspect_tags=[]
        )
    
    try:
        raw_result = await voc_chain.ainvoke({
            "review_text": review_text,
            "format_instructions": parser.get_format_instructions()
        })
        
        return VoCMetadata(**raw_result)
        
    except Exception as e:
        logger.error(f"Error extrayendo metadatos VoC: {e}")
        return VoCMetadata(
            sentiment="neutral",
            category="General",
            aspect_tags=[]
        )