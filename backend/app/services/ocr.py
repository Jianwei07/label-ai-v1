import logging
from pathlib import Path
from typing import List
import asyncio
from pydantic import BaseModel

# Import EasyOCR instead of Tesseract
try:
    import easyocr
except ImportError:
    easyocr = None
    logging.warning(
        "easyocr not installed. OCR functionality will be disabled. "
        "Install with: poetry add easyocr torch torchvision numpy"
    )

from app.core.config import settings
from app.utils.custom_exceptions import OCRProcessingError, ConfigurationError

logger = logging.getLogger(settings.APP_NAME)

# --- Pydantic Model for Structured OCR Data ---
class OCRData(BaseModel):
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float

# --- Initialize EasyOCR Reader ---
# It's a best practice to initialize this once and reuse it.
reader = None
if easyocr:
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        logger.info("EasyOCR Reader initialized successfully for language: ['en']")
    except Exception as e:
        logger.error(f"Failed to initialize EasyOCR Reader: {e}", exc_info=True)


async def extract_text_from_image(image_path: Path, lang: str = 'en') -> List[OCRData]:
    """
    Extracts text and bounding box information from an image using EasyOCR.
    """
    if not reader:
        raise ConfigurationError("EasyOCR is not installed or the Reader failed to initialize.")

    logger.info(f"Starting EasyOCR process for image: {image_path}")

    try:
        path_str = str(image_path)
        
        # Run the synchronous readtext function in a separate thread
        ocr_results = await asyncio.to_thread(reader.readtext, path_str)
        
        extracted_data: List[OCRData] = []
        for (bbox, text, conf) in ocr_results:
            top_left = bbox[0]
            bottom_right = bbox[2]
            
            extracted_data.append(OCRData(
                text=text,
                left=int(top_left[0]),
                top=int(top_left[1]),
                width=int(bottom_right[0] - top_left[0]),
                height=int(bottom_right[1] - top_left[1]),
                confidence=float(conf)
            ))

        logger.info(f"EasyOCR completed for {image_path}. Extracted {len(extracted_data)} text segments.")
        if not extracted_data:
            logger.warning(f"No text segments extracted from {image_path} with sufficient confidence.")
            
        return extracted_data

    except Exception as e:
        logger.error(f"Unexpected error during EasyOCR processing for {image_path}: {e}", exc_info=True)
        raise OCRProcessingError(f"An unexpected error occurred during EasyOCR: {e}")

