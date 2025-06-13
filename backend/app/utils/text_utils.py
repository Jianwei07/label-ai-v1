import logging
import re
from typing import List, Tuple
from thefuzz import fuzz
import numpy as np

from app.core.config import settings
from app.services.ocr import OCRData # Import the OCRData model for type hinting

logger = logging.getLogger(settings.APP_NAME)

def normalize_text(text: str, case_sensitive: bool = True) -> str:
    if not text:
        return ""
    normalized = text.strip()
    if not case_sensitive:
        normalized = normalized.lower()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def compare_text_exactly(text1: str, text2: str, case_sensitive: bool = True) -> bool:
    norm_text1 = normalize_text(text1, case_sensitive)
    norm_text2 = normalize_text(text2, case_sensitive)
    return norm_text1 == norm_text2

def get_text_similarity_ratio(text1: str, text2: str) -> float:
    """
    Calculates similarity. token_set_ratio is good for finding subsets.
    """
    if not text1 or not text2:
        return 0.0
    # Use token_set_ratio which is better for finding text that is a subset of another.
    return fuzz.token_set_ratio(text1, text2, force_ascii=False) / 100.0

def reconstruct_text_blocks(ocr_data: List[OCRData]) -> List[OCRData]:
    """
    Intelligently stitches OCR text segments into coherent lines and blocks.
    """
    if not ocr_data:
        return []

    logger.info("Reconstructing text blocks from OCR data...")
    reconstructed_lines = []
    
    # Sort words by their vertical position first, then horizontal
    ocr_data.sort(key=lambda item: (item.top, item.left))

    # Group words into lines based on vertical alignment
    current_line = []
    for item in ocr_data:
        if not current_line:
            current_line.append(item)
            continue
        
        # Check if the new item is vertically aligned with the current line
        # A simple check is if the vertical midpoint is close to the previous item's midpoint
        previous_item = current_line[-1]
        vertical_midpoint_prev = previous_item.top + previous_item.height / 2
        vertical_midpoint_curr = item.top + item.height / 2

        if abs(vertical_midpoint_curr - vertical_midpoint_prev) < (previous_item.height * 0.7):
            current_line.append(item)
        else:
            # New line detected
            reconstructed_lines.append(current_line)
            current_line = [item]
    
    if current_line:
        reconstructed_lines.append(current_line)

    # Now, merge the words in each line into a single OCRData object per line
    line_blocks = []
    for line in reconstructed_lines:
        if not line: continue
        line.sort(key=lambda item: item.left) # Ensure words are in left-to-right order
        
        full_text = " ".join([item.text for item in line])
        
        # Create a bounding box that encompasses all words in the line
        min_left = min(item.left for item in line)
        min_top = min(item.top for item in line)
        max_right = max(item.left + item.width for item in line)
        max_bottom = max(item.top + item.height for item in line)
        
        avg_confidence = np.mean([item.confidence for item in line])

        line_blocks.append(OCRData(
            text=full_text,
            left=min_left,
            top=min_top,
            width=max_right - min_left,
            height=max_bottom - min_top,
            confidence=avg_confidence
        ))

    logger.info(f"Reconstructed {len(line_blocks)} lines from {len(ocr_data)} OCR segments.")
    return line_blocks

