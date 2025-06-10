import logging
import re
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(settings.APP_NAME)

def normalize_text(text: str, case_sensitive: bool = True) -> str:
    """
    Normalizes text for comparison.
    - Strips leading/trailing whitespace.
    - Optionally converts to lowercase.
    - Can be expanded to handle multiple spaces, special characters, etc.
    """
    if not text:
        return ""
    
    normalized = text.strip()
    if not case_sensitive:
        normalized = normalized.lower()
    
    # Example: Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    logger.debug(f"Normalized text: '{text}' -> '{normalized}' (case_sensitive={case_sensitive})")
    return normalized

def compare_text_exactly(text1: str, text2: str, case_sensitive: bool = True) -> bool:
    """
    Compares two text strings for exact match after normalization.
    """
    norm_text1 = normalize_text(text1, case_sensitive)
    norm_text2 = normalize_text(text2, case_sensitive)
    return norm_text1 == norm_text2

def find_text_occurrences(text_to_find: str, document_text: str, case_sensitive: bool = True) -> List[Tuple[int, int]]:
    """
    Finds all occurrences of a substring in a larger text and returns their start/end indices.
    This is a simple version; for complex documents, OCR data with coordinates is better.
    """
    # This function is less useful if you have OCR with bounding boxes for each word.
    # It's more for searching within a block of extracted text.
    
    flags = 0 if case_sensitive else re.IGNORECASE
    occurrences = []
    for match in re.finditer(re.escape(text_to_find), document_text, flags=flags):
        occurrences.append((match.start(), match.end()))
    logger.debug(f"Found {len(occurrences)} occurrences of '{text_to_find}' in document (case_sensitive={case_sensitive}).")
    return occurrences

# Add more text utility functions as needed, e.g.:
# - Language detection (if not provided by OCR)
# - Levenshtein distance for fuzzy matching (if "exact" has some tolerance defined by sensitivity)
# - Tokenization, stemming (less likely for "exact match" regulatory checks)
