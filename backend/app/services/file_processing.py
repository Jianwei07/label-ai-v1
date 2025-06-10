import logging
import shutil
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile

from app.core.config import settings
from app.utils.custom_exceptions import FileProcessingError

logger = logging.getLogger(settings.APP_NAME)

async def save_upload_file_temp(upload_file: UploadFile, destination_dir: Path) -> Path:
    """
    Saves an uploaded file to a temporary location with a unique name.
    Args:
        upload_file: The FastAPI UploadFile object.
        destination_dir: The directory where the file should be saved.
    Returns:
        Path to the saved file.
    Raises:
        FileProcessingError: If saving fails.
    """
    try:
        if not upload_file.filename:
            raise FileProcessingError("Uploaded file has no filename.")

        # Create a unique filename to avoid collisions
        # Suffix from original filename helps identify file type
        suffix = Path(upload_file.filename).suffix
        unique_filename = f"{uuid4()}{suffix}"
        file_path = destination_dir / unique_filename

        # Ensure destination directory exists
        destination_dir.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        logger.info(f"File '{upload_file.filename}' saved temporarily as '{file_path}'")
        return file_path
    except IOError as e:
        logger.error(f"IOError saving file '{upload_file.filename}': {e}", exc_info=True)
        raise FileProcessingError(f"Could not save file: {upload_file.filename}. IO Error.")
    except Exception as e:
        logger.error(f"Unexpected error saving file '{upload_file.filename}': {e}", exc_info=True)
        raise FileProcessingError(f"An unexpected error occurred while saving file: {upload_file.filename}.")
    finally:
        await upload_file.close()


async def cleanup_temp_file(file_path: Path) -> None:
    """
    Deletes a temporary file.
    Args:
        file_path: Path to the file to be deleted.
    """
    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.info(f"Temporary file '{file_path}' deleted successfully.")
        else:
            logger.warning(f"Temporary file '{file_path}' not found or is not a file for cleanup.")
    except Exception as e:
        logger.error(f"Error deleting temporary file '{file_path}': {e}", exc_info=True)
        # Not raising an exception here as cleanup failure might not be critical path
        # but should be logged. Depending on requirements, you might want to raise.

async def store_processed_image(image_path: Path, analysis_id: str) -> Path:
    """
    (Optional) Stores a processed image (e.g., with highlights) in a structured way.
    For example, in settings.STATIC_SERVED_DIR for retrieval via API.
    Args:
        image_path: Path to the processed image.
        analysis_id: A unique ID for the analysis to name the stored file.
    Returns:
        Path to the stored processed image.
    """
    try:
        destination_dir = settings.STATIC_SERVED_DIR / "processed_labels"
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        stored_filename = f"{analysis_id}{image_path.suffix}"
        stored_image_path = destination_dir / stored_filename

        shutil.copy(image_path, stored_image_path)
        logger.info(f"Processed image for analysis '{analysis_id}' stored at '{stored_image_path}'")
        return stored_image_path
    except Exception as e:
        logger.error(f"Error storing processed image for analysis '{analysis_id}': {e}", exc_info=True)
        raise FileProcessingError(f"Could not store processed image for analysis '{analysis_id}'.")

