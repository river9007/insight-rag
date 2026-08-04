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
# Soporta IDs alfanuméricos como PROD-AUDIO-01 o PROD-1234
REVIEW_PATTERN = re.compile(
    r"ID\s+de\s+Producto\s*:\s*(?P<product_id>PROD-[A-Z0-9_-]+)\s*"
    r"(?:\(\s*(?P<product_name>[^)]+?)\s*\)\s*)?"
    r"Rating\s*:\s*(?P<rating>\d+)\s*"
    r"Rese[ñn]a\s*:\s*(?P<text>.*?)"
    r"(?=ID\s+de\s+Producto\s*:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

def parse_reviews(full_text: str) -> List[ParsedReview]:
    """
    Extrae reseñas individuales de texto no estructurado (PDF / TXT).
    """
    reviews = []
    for match in REVIEW_PATTERN.finditer(full_text):
        raw_text = match.group("text").strip()
        clean_text = re.sub(r"\s+", " ", raw_text)

        p_id = match.group("product_id").strip()
        p_name = match.group("product_name")
        p_name = p_name.strip() if p_name else p_id

        reviews.append(
            ParsedReview(
                product_id=p_id,
                product_name=p_name,
                rating=int(match.group("rating")),
                text=clean_text,
            )
        )
    return reviews