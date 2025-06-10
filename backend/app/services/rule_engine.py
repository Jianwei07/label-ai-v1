import logging
from pathlib import Path
from uuid import UUID
from typing import List, Dict, Any
import datetime

from app.core.config import settings
from app.api.v1 import schemas as api_schemas
from app.services import ocr, visual_analysis
from app.utils import text_utils, image_utils
from app.utils.custom_exceptions import RuleEngineError
from app.crud import crud_analysis
from app.services import file_processing as file_processing

logger = logging.getLogger(settings.APP_NAME)

# Helper to create a fault highlight when the location is unknown
def _create_generic_fault_highlight(rule_id_ref: str, message: str) -> api_schemas.HighlightedElement:
    """Creates a small red box in the top-left corner for faults without a specific location."""
    return api_schemas.HighlightedElement(
        rule_id_ref=rule_id_ref,
        bounding_box=api_schemas.BoundingBox(x=5, y=5, width=20, height=20),
        status="wrong",
        message=message,
        found_value="Not Applicable",
        expected_value="Varies per rule",
    )


async def process_label_analysis_sync(
    analysis_id: UUID,
    image_path: Path,
    ruleset: api_schemas.RuleSet,
    sensitivity: int,
    original_filename: str
) -> api_schemas.LabelAnalysisResult:
    """
    Orchestrates the entire label analysis, and now saves the result to the database.
    """
    logger.info(f"Starting analysis (ID: {analysis_id}) for image: {image_path.name}")
    
    highlights: List[api_schemas.HighlightedElement] = []
    faults_without_highlights: List[str] = [] # This list is for logging, not highlights
    matches_count = 0
    mismatches_count = 0

    all_ocr_data = await ocr.extract_text_from_image(image_path)
    detected_barcodes = await visual_analysis.detect_and_measure_barcode(image_path)

    for i, condition in enumerate(ruleset.conditions):
        rule_id_ref = f"rule_{i+1}_{condition.type.value}"
        
        try:
            if condition.type == api_schemas.RuleType.EXACT_TEXT_MATCH:
                found_match = False
                if not condition.expected_text: continue

                normalized_expected = text_utils.normalize_text(condition.expected_text, case_sensitive=False)
                for ocr_item in all_ocr_data:
                    normalized_ocr = text_utils.normalize_text(ocr_item.text, case_sensitive=False)

                    if normalized_expected in normalized_ocr:
                        is_exact = text_utils.compare_text_exactly(ocr_item.text, condition.expected_text, case_sensitive=condition.case_sensitive)
                        status = "correct" if is_exact else "wrong"
                        message = f"Found expected text: '{condition.expected_text}'" if is_exact else f"Found similar text '{ocr_item.text}', but not an exact match."
                        
                        highlights.append(api_schemas.HighlightedElement(
                            rule_id_ref=rule_id_ref,
                            bounding_box=api_schemas.BoundingBox(x=ocr_item.left, y=ocr_item.top, width=ocr_item.width, height=ocr_item.height),
                            status=status,
                            message=message,
                            found_value=ocr_item.text,
                            expected_value=condition.expected_text,
                        ))
                        
                        if is_exact: matches_count += 1
                        else: mismatches_count += 1
                        found_match = True
                        break
                
                if not found_match:
                    mismatches_count += 1
                    fault_message = f"Missing required text: '{condition.expected_text}'"
                    faults_without_highlights.append(fault_message)
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, fault_message))


            elif condition.type == api_schemas.RuleType.BARCODE_DIMENSIONS:
                if not detected_barcodes:
                    mismatches_count += 1
                    faults_without_highlights.append("Barcode check failed: No barcodes detected on label.")
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, "No barcode detected on label to check dimensions."))
                    continue
                
                barcode_to_check = next((bc for bc in detected_barcodes if bc.get("data") == condition.target_element_description), None)
                
                if not barcode_to_check:
                    mismatches_count += 1
                    fault_message = f"Could not find barcode with data '{condition.target_element_description}' to check its dimensions."
                    faults_without_highlights.append(fault_message)
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, fault_message))
                    continue

                width_ok = True
                if condition.expected_width_mm is not None:
                    width_ok = abs(barcode_to_check['measured_width_mm'] - condition.expected_width_mm) <= (condition.tolerance_mm or 0.5)

                height_ok = True
                if condition.expected_height_mm is not None:
                    height_ok = abs(barcode_to_check['measured_height_mm'] - condition.expected_height_mm) <= (condition.tolerance_mm or 0.5)
                
                status = "correct" if width_ok and height_ok else "wrong"
                if status == "correct": matches_count += 1
                else: mismatches_count += 1
                
                message = f"Barcode ({barcode_to_check['data']}) dimensions are valid." if status == 'correct' else f"Barcode ({barcode_to_check['data']}) dimensions are invalid. Found: W={barcode_to_check['measured_width_mm']:.2f}mm, H={barcode_to_check['measured_height_mm']:.2f}mm"
                
                highlights.append(api_schemas.HighlightedElement(
                    rule_id_ref=rule_id_ref,
                    bounding_box=barcode_to_check['bounding_box'],
                    status=status,
                    message=message,
                    expected_value=f"W:{condition.expected_width_mm}mm, H:{condition.expected_height_mm}mm"
                ))

            # Other rules like FONT_SIZE can be filled in with similar logic
            else:
                mismatches_count += 1 # Temporarily count unimplemented rules as mismatches
                faults_without_highlights.append(f"Rule type '{condition.type.value}' for '{condition.target_element_description}' not fully implemented.")


        except Exception as e:
            logger.error(f"Error processing rule '{rule_id_ref}': {e}", exc_info=True)
            mismatches_count += 1
            faults_without_highlights.append(f"Failed to process rule for '{condition.target_element_description or 'Unknown Target'}'.")

    # --- Construct Final Result ---
    overall_status = "pass" if mismatches_count == 0 else "fail_minor"
    summary = {
        "total_rules_defined": len(ruleset.conditions),
        "matches": matches_count,
        "mismatches_or_errors_in_rules": mismatches_count,
        "faults_without_highlights": faults_without_highlights
    }

    result_object = api_schemas.LabelAnalysisResult(
        analysis_id=analysis_id,
        original_filename=original_filename,
        overall_status=overall_status,
        summary=summary,
        highlights=highlights,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # --- Save evidence to persistent storage ---
    processed_image_path_str = None
    try:
        output_image_path = settings.UPLOADS_DIR / f"processed_{analysis_id}.png"
        await image_utils.draw_bounding_boxes_on_image(image_path, highlights, output_image_path)
        stored_image_path = await file_processing.store_processed_image(output_image_path, str(analysis_id))
        processed_image_path_str = str(stored_image_path.relative_to(settings.STATIC_SERVED_DIR))
        await file_processing.cleanup_temp_file(output_image_path)
    except Exception as e:
        logger.error(f"Could not generate or save highlighted image for analysis {analysis_id}: {e}", exc_info=True)

    try:
        await crud_analysis.create_analysis(
            result_data=result_object,
            initial_ruleset=ruleset,
            processed_image_path=processed_image_path_str
        )
        logger.info(f"Successfully saved analysis result {analysis_id} to database.")
    except Exception as e:
        logger.error(f"Failed to save analysis result {analysis_id} to database: {e}", exc_info=True)

    return result_object
