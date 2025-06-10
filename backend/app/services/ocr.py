import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import asyncio # For running synchronous Tesseract in a thread
import cv2 # For the conversion if not already imported

from app.core.config import settings
from app.utils import image_utils
from app.utils.custom_exceptions import OCRProcessingError, ConfigurationError
from pydantic import BaseModel  # <-- Add this import


# Attempt to import Tesseract related libraries
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None
    logging.warning(
        "pytesseract or Pillow (PIL) not installed. OCR functionality will be disabled. "
        "Install with: poetry add pytesseract Pillow"
    )


logger = logging.getLogger(settings.APP_NAME)

# Configure Tesseract path if specified in settings
if pytesseract and settings.TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
    logger.info(f"Tesseract command path set to: {settings.TESSERACT_PATH}")

class OCRData(BaseModel): # Using Pydantic for structured data
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float # Tesseract's confidence score for the word/block

async def extract_text_from_image(image_path: Path, lang: str = 'eng') -> List[OCRData]:
    """
    Extracts text and bounding box information from an image using Tesseract OCR.
    Args:
        image_path: Path to the image file.
        lang: Language for OCR (e.g., 'eng', 'fra', 'eng+fra').
    Returns:
        A list of OCRData objects, each representing a detected text segment.
    Raises:
        ConfigurationError: If Tesseract is not available.
        OCRProcessingError: If OCR fails.
    """
    if not pytesseract or not Image:
        raise ConfigurationError("Pytesseract or Pillow (PIL) is not installed. OCR functionality is disabled.")

    logger.info(f"Starting OCR process for image: {image_path} with language: {lang}")

    try:
        # Preprocess the image for potentially better OCR results
        # Note: image_utils.load_image returns a cv2 image (np.ndarray)
        # Tesseract's image_to_data can take a PIL image or filepath
        # For consistency and if preprocessing is done with OpenCV, convert cv2 image to PIL
        
        # Option 1: Pass filepath directly (Tesseract handles loading)
        # preprocessed_image_path = image_path # Or path to a preprocessed image file

        # Option 2: Load with OpenCV, preprocess, then pass to Tesseract
        # This gives more control over preprocessing steps.
        cv_image = await image_utils.load_image(image_path)
        preprocessed_cv_image = await image_utils.preprocess_image_for_ocr(cv_image)
        
        # Convert OpenCV image (NumPy array, BGR) to PIL Image (RGB)
        pil_image = Image.fromarray(cv2.cvtColor(preprocessed_cv_image, cv2.COLOR_BGR2RGB))


        # Run Tesseract OCR - this is a synchronous (blocking) call
        # Use asyncio.to_thread to run it in a separate thread to avoid blocking FastAPI's event loop
        # Output type: 'data.frame' for pandas DataFrame, 'dict' for dict
        ocr_df = await asyncio.to_thread(
            pytesseract.image_to_data,
            pil_image, # or preprocessed_image_path
            lang=lang,
            output_type=pytesseract.Output.DATAFRAME # Pandas DataFrame
            # config='--psm 6' # Example Tesseract config: Assume a single uniform block of text.
        )
        
        # Filter out entries with low confidence or no text
        ocr_df = ocr_df[ocr_df.conf > -1] # Tesseract uses -1 for items that are not words
        ocr_df = ocr_df.dropna(subset=['text']) # Remove rows where text is NaN
        ocr_df = ocr_df[ocr_df.text.str.strip() != ''] # Remove empty strings

        extracted_data: List[OCRData] = []
        for index, row in ocr_df.iterrows():
            extracted_data.append(OCRData(
                text=str(row['text']),
                left=int(row['left']),
                top=int(row['top']),
                width=int(row['width']),
                height=int(row['height']),
                confidence=float(row['conf']) / 100.0 # Convert from 0-100 to 0.0-1.0
            ))
        
        logger.info(f"OCR completed for {image_path}. Extracted {len(extracted_data)} text segments.")
        if not extracted_data:
            logger.warning(f"No text segments extracted from {image_path} with sufficient confidence.")
            
        return extracted_data

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract is not installed or not found in your PATH. Please install Tesseract OCR.")
        raise ConfigurationError("Tesseract OCR is not installed or not found.")
    except RuntimeError as e: # Tesseract can raise RuntimeError for various issues
        logger.error(f"Runtime error during Tesseract OCR processing for {image_path}: {e}", exc_info=True)
        raise OCRProcessingError(f"Tesseract runtime error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during OCR for {image_path}: {e}", exc_info=True)
        raise OCRProcessingError(f"An unexpected error occurred during OCR: {e}")

# Helper Pydantic model for structured OCR data (already defined in schemas.py or similar,
# but can be defined locally if service specific)

class OCRData(BaseModel):
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float
