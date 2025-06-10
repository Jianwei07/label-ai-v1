import logging
from pathlib import Path
from typing import List
import asyncio
import numpy as np
from pydantic import BaseModel

# Import EasyOCR instead of Tesseract
try:
    import easyocr
except ImportError:
    easyocr = None
    logging.warning(
        "easyocr not installed. OCR functionality will be disabled. "
        "Install with: poetry add easyocr torch torchvision"
    )

from app.core.config import settings
from app.utils.custom_exceptions import OCRProcessingError, ConfigurationError

logger = logging.getLogger(settings.APP_NAME)

# --- Pydantic Model for Structured OCR Data ---
# This remains the same, as it defines the data structure the rest of our app expects.
class OCRData(BaseModel):
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float

# --- Initialize EasyOCR Reader ---
# It's a best practice to initialize this once and reuse it.
# The first time this is run, EasyOCR will download the necessary language models.
# This might take a moment and requires an internet connection.
reader = None
if easyocr:
    try:
        # We specify English ('en') here. You can add more languages like ['en', 'fr'].
        reader = easyocr.Reader(['en'], gpu=False) # Use gpu=True if you have a compatible GPU and CUDA setup
        logger.info("EasyOCR Reader initialized successfully for language: ['en']")
    except Exception as e:
        logger.error(f"Failed to initialize EasyOCR Reader: {e}", exc_info=True)
        # The service will fail gracefully if the reader isn't initialized.


async def extract_text_from_image(image_path: Path, lang: str = 'en') -> List[OCRData]:
    """
    Extracts text and bounding box information from an image using EasyOCR.
    Args:
        image_path: Path to the image file.
        lang: Language(s) for OCR (Note: EasyOCR reader is pre-initialized with languages).
    Returns:
        A list of OCRData objects, each representing a detected text segment.
    Raises:
        ConfigurationError: If EasyOCR is not available or failed to initialize.
        OCRProcessingError: If OCR processing fails for other reasons.
    """
    if not reader:
        raise ConfigurationError("EasyOCR is not installed or the Reader failed to initialize.")

    logger.info(f"Starting EasyOCR process for image: {image_path}")

    try:
        # EasyOCR's readtext is a synchronous (blocking) call.
        # We run it in a separate thread to keep the FastAPI server responsive.
        # It can accept a file path directly.
        path_str = str(image_path)
        
        ocr_results = await asyncio.to_thread(reader.readtext, path_str)
        
        extracted_data: List[OCRData] = []
        for (bbox, text, conf) in ocr_results:
            # The bbox from EasyOCR is a list of four [x, y] coordinates (top-left, top-right, bottom-right, bottom-left)
            # We need to convert this to our standard (x, y, width, height) format.
            top_left = bbox[0]
            bottom_right = bbox[2]
            
            x = int(top_left[0])
            y = int(top_left[1])
            width = int(bottom_right[0] - top_left[0])
            height = int(bottom_right[1] - top_left[1])
            
            extracted_data.append(OCRData(
                text=text,
                left=x,
                top=y,
                width=width,
                height=height,
                confidence=float(conf)
            ))

        logger.info(f"EasyOCR completed for {image_path}. Extracted {len(extracted_data)} text segments.")
        if not extracted_data:
            logger.warning(f"No text segments extracted from {image_path} with sufficient confidence.")
            
        return extracted_data

    except Exception as e:
        logger.error(f"Unexpected error during EasyOCR processing for {image_path}: {e}", exc_info=True)
        raise OCRProcessingError(f"An unexpected error occurred during EasyOCR: {e}")