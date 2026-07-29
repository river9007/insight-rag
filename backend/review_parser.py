# Archivo: backend/review_parser.py
import re
from dataclasses import dataclass
from typing import List

@dataclass
class ParsedReview:
    product_id: str
    product_name: str
    rating: int
    text: str

# Reconoce bloques con las 3 etiquetas: "ID de Producto", "Rating", "Reseña".
# re.IGNORECASE + \s* flexible: tolera variaciones de mayúsculas y espacios/saltos
# de línea (comunes al extraer texto de PDF), pero requiere estas etiquetas
# exactas. Un formato con etiquetas distintas (ej. en inglés) necesitaría un
# patrón adicional — no se intenta adivinar formatos que aún no se han visto.
REVIEW_PATTERN = re.compile(
    r"ID\s+de\s+Producto\s*:\s*(?P<product_id>PROD-\d+)\s*"
    r"\(\s*(?P<product_name>[^)]+?)\s*\)\s*"
    r"Rating\s*:\s*(?P<rating>\d+)\s*"
    r"Rese[ñn]a\s*:\s*(?P<text>.*?)"
    r"(?=ID\s+de\s+Producto\s*:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

def parse_reviews(full_text: str) -> List[ParsedReview]:
    """
    Extrae reseñas individuales de un texto con el formato:
    'ID de Producto: PROD-XXXX (Nombre) Rating: N Reseña: texto...'

    Devuelve una lista vacía si el texto no contiene ningún bloque
    reconocible — el llamador decide qué hacer en ese caso.
    """
    reviews = []
    for match in REVIEW_PATTERN.finditer(full_text):
        raw_text = match.group("text").strip()
        # Normaliza saltos de línea y espacios múltiples que deja pypdf
        clean_text = re.sub(r"\s+", " ", raw_text)

        reviews.append(
            ParsedReview(
                product_id=match.group("product_id").strip(),
                product_name=match.group("product_name").strip(),
                rating=int(match.group("rating")),
                text=clean_text,
            )
        )
    return reviews
