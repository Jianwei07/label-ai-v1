import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, status
from typing import Optional
from uuid import UUID, uuid4

from app.core.config import settings
from app.api.v1 import schemas
# Use the full service names for clarity
from app.services import (
    file_processing,
    ocr,
    pdf_parser, # This service will now also handle .docx
    visual_analysis,
    rule_engine
)
from app.utils.custom_exceptions import CoreServiceError

logger = logging.getLogger(settings.APP_NAME)
router = APIRouter()

@router.post(
    "/check",
    response_model=schemas.LabelAnalysisResult,
    summary="Analyze a Label Image Against Rules",
    description="Upload a label image and a rules document (JSON, YAML, or DOCX) to perform regulatory checks.",
    status_code=status.HTTP_200_OK
)
async def check_label_compliance(
    background_tasks: BackgroundTasks,
    label_image: UploadFile = File(..., description="The label image file (e.g., PNG, JPG)."),
    rules_json_str: Optional[str] = Form(None, description="RuleSet provided as a JSON string. Use this OR rules_file."),
    rules_file: Optional[UploadFile] = File(None, description="A file (JSON, YAML, or DOCX) containing the rules. Use this OR rules_json_str."),
    sensitivity: Optional[int] = Form(50, ge=0, le=100, description="Global sensitivity for checking (0-100)."),
):
    logger.info(f"Received label check request for image: {label_image.filename}")

    if not label_image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Label image must be an image file.")

    parsed_ruleset: Optional[schemas.RuleSet] = None

    if rules_json_str:
        try:
            parsed_ruleset = schemas.RuleSet.model_validate_json(rules_json_str)
            logger.info(f"Successfully parsed RuleSet from JSON string: {parsed_ruleset.name}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid rules_json_str format: {e}")
    elif rules_file:
        # UPDATED: Added '.docx' to the list of accepted file types
        allowed_extensions = {".json", ".yaml", ".yml", ".docx"}
        if not any(rules_file.filename.endswith(ext) for ext in allowed_extensions):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rules file must be JSON, YAML, or DOCX.")
        try:
            rules_content = await rules_file.read()
            # The service will determine how to parse based on filename
            parsed_ruleset = await pdf_parser.parse_rules_from_content(rules_content, rules_file.filename)
            logger.info(f"Successfully parsed RuleSet from file: {rules_file.filename}")
        except CoreServiceError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either rules_json_str or rules_file must be provided.")

    if not parsed_ruleset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RuleSet could not be determined from the provided input.")

    try:
        saved_image_path = await file_processing.save_upload_file_temp(label_image, settings.UPLOADS_DIR)
        analysis_id = uuid4()
        
        analysis_result = await rule_engine.process_label_analysis_sync(
            analysis_id=analysis_id,
            image_path=saved_image_path,
            ruleset=parsed_ruleset,
            sensitivity=sensitivity,
            original_filename=label_image.filename or "unknown_image"
        )
        
        # Cleanup can be run in the background after the response is sent
        background_tasks.add_task(file_processing.cleanup_temp_file, saved_image_path)

        return analysis_result
    except CoreServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message, headers=e.headers)
    except Exception as e:
        logger.critical(f"Unexpected critical error during label check: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during label processing.")
