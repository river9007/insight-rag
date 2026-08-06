# Archivo: backend/review_parser.py
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ParsedReview:
    product_id: str
    product_name: str
    rating: int
    text: str
    category: str = "General"

# Reconoce bloques con etiquetas: "ID de Producto", "(Nombre del producto opcional)", 
# "Categoría (opcional)", "Rating", "Reseña".
REVIEW_PATTERN = re.compile(
    r"ID\s+de\s+Producto\s*:\s*(?P<product_id>PROD-[A-Z0-9_-]+)\s*"
    r"(?:\(\s*(?P<product_name>[^)]+?)\s*\)\s*)?"
    r"(?:\s*Categor[ií]a\s*:\s*(?P<category>[^\n\r]+?)\s*)?"
    r"Rating\s*:\s*(?P<rating>\d+)\s*"
    r"Rese[ñn]a\s*:\s*(?P<text>.*?)"
    r"(?=ID\s+de\s+Producto\s*:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

def parse_reviews(full_text: str) -> List[ParsedReview]:
    """
    Extrae reseñas individuales de texto no estructurado (PDF / TXT).
    Soporta opcionalmente el campo Categoría sin romper archivos legacy.
    """
    reviews = []
    for match in REVIEW_PATTERN.finditer(full_text):
        raw_text = match.group("text").strip()
        clean_text = re.sub(r"\s+", " ", raw_text)

        p_id = match.group("product_id").strip()
        p_name = match.group("product_name")
        p_name = p_name.strip() if p_name else p_id
        
        cat = match.group("category")
        cat_name = cat.strip() if cat else "General"

        reviews.append(
            ParsedReview(
                product_id=p_id,
                product_name=p_name,
                rating=int(match.group("rating")),
                text=clean_text,
                category=cat_name
            )
        )
    return reviews