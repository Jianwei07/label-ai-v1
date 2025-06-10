import logging
from app.api.v1 import schemas
import cv2 # OpenCV
import numpy as np
from PIL import Image # Pillow for image manipulation
from typing import Any,Dict, Optional, Tuple, List, Union
from pathlib import Path

from app.core.config import settings
from app.utils.custom_exceptions import VisualAnalysisError, FileProcessingError
from app.api.v1.schemas import BoundingBox # For type hinting

logger = logging.getLogger(settings.APP_NAME)

async def load_image(image_path: Union[str, Path]) -> np.ndarray:
    """
    Loads an image from the given path using OpenCV.
    Returns:
        np.ndarray: The loaded image in BGR format.
    Raises:
        FileProcessingError: If the image cannot be loaded.
    """
    try:
        path_str = str(image_path)
        img = cv2.imread(path_str)
        if img is None:
            logger.error(f"Failed to load image from path: {path_str}. File might be corrupted or not an image.")
            raise FileProcessingError(f"Could not load image from path: {path_str}")
        logger.debug(f"Image loaded from {path_str}, shape: {img.shape}")
        return img
    except Exception as e:
        logger.error(f"Unexpected error loading image {image_path}: {e}", exc_info=True)
        raise FileProcessingError(f"Unexpected error loading image: {e}")

async def preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Preprocesses an image for better OCR results.
    Steps:
    1. Convert to grayscale.
    2. Apply thresholding (e.g., Otsu's binarization).
    3. Optional: Noise reduction, deskewing.
    """
    logger.debug("Preprocessing image for OCR...")
    try:
        # Convert to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding for better results on varying lighting
        # processed_image = cv2.adaptiveThreshold(
        #     gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        #     cv2.THRESH_BINARY, 11, 2
        # )
        
        # Or Otsu's binarization after Gaussian blur
        blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
        _, processed_image = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Optional: Further noise reduction
        # processed_image = cv2.medianBlur(processed_image, 3)

        logger.debug("Image preprocessing for OCR complete.")
        return processed_image
    except cv2.error as e:
        logger.error(f"OpenCV error during OCR preprocessing: {e}", exc_info=True)
        raise VisualAnalysisError(f"OpenCV error during OCR preprocessing: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during OCR preprocessing: {e}", exc_info=True)
        raise VisualAnalysisError(f"Unexpected error during OCR preprocessing: {e}")


async def draw_bounding_boxes_on_image(
    image_path: Union[str, Path],
    highlights: List[schemas.HighlightedElement], # Using the schema
    output_path: Union[str, Path]
) -> str:
    """
    Draws bounding boxes on an image based on highlight information.
    Saves the modified image to output_path.
    Args:
        image_path: Path to the original image.
        highlights: List of HighlightedElement objects.
        output_path: Path to save the new image with highlights.
    Returns:
        str: Path to the saved image with highlights.
    Raises:
        FileProcessingError or VisualAnalysisError on failure.
    """
    logger.info(f"Drawing bounding boxes on image: {image_path}")
    img = await load_image(image_path)

    for highlight in highlights:
        box = highlight.bounding_box
        color = (0, 255, 0) if highlight.status == "correct" else \
                (0, 0, 255) if highlight.status == "wrong" else \
                (255, 0, 0) # Blue for 'info' or other statuses
        thickness = 2 # Can be adjusted

        # Draw rectangle
        cv2.rectangle(img, (box.x, box.y), (box.x + box.width, box.y + box.height), color, thickness)

        # Add tooltip text (simple version, can be enhanced)
        # For complex tooltips, this might be better handled by frontend overlay
        # text_y_position = box.y - 10 if box.y - 10 > 10 else box.y + box.height + 20
        # cv2.putText(img, highlight.message[:50], (box.x, text_y_position),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    try:
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), img)
        logger.info(f"Image with highlights saved to: {output_path}")
        return str(output_path)
    except cv2.error as e:
        logger.error(f"OpenCV error saving image with highlights: {e}", exc_info=True)
        raise VisualAnalysisError(f"OpenCV error saving image with highlights: {e}")
    except Exception as e:
        logger.error(f"Error saving image {output_path}: {e}", exc_info=True)
        raise FileProcessingError(f"Could not save image with highlights: {e}")


async def get_image_dimensions(image_path: Union[str, Path]) -> Tuple[int, int]:
    """Gets the width and height of an image."""
    try:
        img = await load_image(image_path)
        height, width, _ = img.shape
        return width, height
    except Exception as e:
        logger.error(f"Could not get dimensions for image {image_path}: {e}", exc_info=True)
        raise FileProcessingError(f"Could not get image dimensions: {e}")

# Placeholder for more advanced visual check functions
async def estimate_font_size_in_roi(image: np.ndarray, roi: BoundingBox, dpi: int = 300) -> Optional[Tuple[float, str]]:
    """
    Placeholder: Estimates font size within a Region of Interest (ROI).
    Args:
        image: The full image as a NumPy array.
        roi: The BoundingBox defining the region of interest.
        dpi: Dots Per Inch of the scanned image, crucial for mm/pt conversion.
    Returns:
        A tuple (size, unit) e.g., (12.0, "pt") or (3.0, "mm"), or None if not determinable.
    """
    logger.debug(f"Estimating font size in ROI: x={roi.x}, y={roi.y}, w={roi.width}, h={roi.height}")
    # Crop ROI
    # Perform contour analysis on characters, estimate height in pixels
    # Convert pixel height to mm or points using DPI
    # This is a complex task.
    # Example: pixel_height_of_char / dpi * 25.4 = height_in_mm
    # Example: pixel_height_of_char * 72 / dpi = height_in_points   
    return (3.0, "mm") # Dummy value

async def check_barcode_dimensions_in_roi(image: np.ndarray, roi: BoundingBox, dpi: int = 300) -> Dict[str, Any]:
    """
    Placeholder: Checks barcode dimensions within an ROI.
    """
    logger.debug(f"Checking barcode dimensions in ROI: x={roi.x}, y={roi.y}, w={roi.width}, h={roi.height}")
    # Detect barcode within ROI (e.g., using zbar or pyzbar with OpenCV)
    # Measure its bounding box in pixels
    # Convert to mm using DPI
    return {"width_mm": 30.0, "height_mm": 20.0, "detected": True} # Dummy values

# Add other utility functions as needed:
# - Cropping ROIs
# - Color analysis
# - Template matching for logos/symbols
# - Spacing analysis between text blocks
