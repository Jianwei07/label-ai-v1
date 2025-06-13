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

# --- THRESHOLDS FOR SMART MATCHING ---
# These can be tuned later or even made part of the request's sensitivity.
PERFECT_MATCH_THRESHOLD = 0.98
NEAR_MATCH_THRESHOLD = 0.85
MINIMUM_SIMILARITY_TO_CONSIDER = 0.60

def _create_generic_fault_highlight(rule_id_ref: str, message: str) -> api_schemas.HighlightedElement:
    """Creates a small red box in the top-left corner for faults without a specific location."""
    return api_schemas.HighlightedElement(
        rule_id_ref=rule_id_ref,
        bounding_box=api_schemas.BoundingBox(x=5, y=5, width=20, height=20),
        status="wrong",
        message=message,
        found_value="Not Found",
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
    Orchestrates the label analysis with smarter text matching logic.
    """
    logger.info(f"Starting analysis (ID: {analysis_id}) for image: {image_path.name}")
    
    highlights: List[api_schemas.HighlightedElement] = []
    faults_without_highlights: List[str] = []
    matches_count = 0
    mismatches_count = 0

    all_ocr_data = await ocr.extract_text_from_image(image_path)
    detected_barcodes = await visual_analysis.detect_and_measure_barcode(image_path)

    # --- NEW: Reconstruct text blocks before checking rules ---
    reconstructed_text_blocks = text_utils.reconstruct_text_blocks(all_ocr_data)
    # Combine original OCR segments with reconstructed blocks for a comprehensive search
    searchable_text_items = all_ocr_data + reconstructed_text_blocks

    for i, condition in enumerate(ruleset.conditions):
        rule_id_ref = f"rule_{i+1}_{condition.type.value}"
        
        try:
            if condition.type == api_schemas.RuleType.EXACT_TEXT_MATCH:
                if not condition.expected_text: continue

                best_match_score = 0
                best_match_item = None

                # Find the best possible match for the rule in all searchable items
                for item in searchable_text_items:
                    score = text_utils.get_text_similarity_ratio(condition.expected_text, item.text)
                    if score > best_match_score:
                        best_match_score = score
                        best_match_item = item

                # Now, evaluate the best match found
                if best_match_score >= PERFECT_MATCH_THRESHOLD:
                    highlights.append(api_schemas.HighlightedElement(
                        rule_id_ref=rule_id_ref,
                        bounding_box=api_schemas.BoundingBox(x=best_match_item.left, y=best_match_item.top, width=best_match_item.width, height=best_match_item.height),
                        status="correct", message=f"Found expected text: '{condition.expected_text}'",
                        found_value=best_match_item.text, expected_value=condition.expected_text
                    ))
                    matches_count += 1
                elif best_match_score >= NEAR_MATCH_THRESHOLD:
                    highlights.append(api_schemas.HighlightedElement(
                        rule_id_ref=rule_id_ref,
                        bounding_box=api_schemas.BoundingBox(x=best_match_item.left, y=best_match_item.top, width=best_match_item.width, height=best_match_item.height),
                        status="wrong", message=f"Found text '{best_match_item.text}', but it's not an exact match for '{condition.expected_text}'. (Similarity: {best_match_score:.0%})",
                        found_value=best_match_item.text, expected_value=condition.expected_text
                    ))
                    mismatches_count += 1
                elif best_match_score < MINIMUM_SIMILARITY_TO_CONSIDER:
                    mismatches_count += 1
                    fault_message = f"Missing required text: '{condition.expected_text}'"
                    faults_without_highlights.append(fault_message)
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, fault_message))
                else:
                    mismatches_count += 1
                    highlights.append(api_schemas.HighlightedElement(
                        rule_id_ref=rule_id_ref,
                        bounding_box=api_schemas.BoundingBox(x=best_match_item.left, y=best_match_item.top, width=best_match_item.width, height=best_match_item.height),
                        status="wrong", message=f"Found text with low similarity: '{best_match_item.text}' for expected text '{condition.expected_text}'. (Similarity: {best_match_score:.0%})",
                        found_value=best_match_item.text, expected_value=condition.expected_text
                    ))
            
            # --- This is the placeholder logic from your file, which we can fill in next ---
            elif condition.type == api_schemas.RuleType.FONT_SIZE:
                 mismatches_count += 1
                 faults_without_highlights.append(f"Rule type '{condition.type.value}' for '{condition.target_element_description}' not fully implemented.")

            elif condition.type == api_schemas.RuleType.BARCODE_DIMENSIONS:
                if not detected_barcodes:
                    mismatches_count += 1
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, "No barcode detected on label to check dimensions."))
                    continue

                barcode_number_rule = next((r for r in ruleset.conditions if r.type == api_schemas.RuleType.EXACT_TEXT_MATCH and r.target_element_description == condition.target_element_description), None)
                if not barcode_number_rule or not barcode_number_rule.expected_text:
                    mismatches_count += 1
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, f"Could not find barcode number in rules for '{condition.target_element_description}'."))
                    continue

                barcode_number_to_find = barcode_number_rule.expected_text
                barcode_to_check = next((bc for bc in detected_barcodes if bc.get("data") == barcode_number_to_find), None)
                
                if not barcode_to_check:
                    mismatches_count += 1
                    highlights.append(_create_generic_fault_highlight(rule_id_ref, f"Could not find barcode with data '{barcode_number_to_find}' on the label."))
                    continue

                width_ok = abs(barcode_to_check['measured_width_mm'] - (condition.expected_width_mm or 0)) <= (condition.tolerance_mm or 0.5) if condition.expected_width_mm is not None else True
                height_ok = abs(barcode_to_check['measured_height_mm'] - (condition.expected_height_mm or 0)) <= (condition.tolerance_mm or 0.5) if condition.expected_height_mm is not None else True
                
                status = "correct" if width_ok and height_ok else "wrong"
                if status == "correct": matches_count += 1
                else: mismatches_count += 1
                
                message = f"Barcode ({barcode_to_check['data']}) dimensions are valid." if status == 'correct' else f"Barcode ({barcode_to_check['data']}) dimensions invalid. Found: W={barcode_to_check['measured_width_mm']:.2f}mm, H={barcode_to_check['measured_height_mm']:.2f}mm"
                
                highlights.append(api_schemas.HighlightedElement(
                    rule_id_ref=rule_id_ref, bounding_box=barcode_to_check['bounding_box'],
                    status=status, message=message,
                    expected_value=f"W:{condition.expected_width_mm}mm, H:{condition.expected_height_mm}mm"
                ))

            else:
                mismatches_count += 1
                faults_without_highlights.append(f"Rule type '{condition.type.value}' for '{condition.target_element_description}' not fully implemented.")

        except Exception as e:
            logger.error(f"Error processing rule '{rule_id_ref}': {e}", exc_info=True)
            mismatches_count += 1
            faults_without_highlights.append(f"Failed to process rule for '{condition.target_element_description or 'Unknown Target'}'.")

    # --- Construct Final Result ---
    overall_status = "pass" if mismatches_count == 0 else "fail_minor"
    summary = {
        "total_rules_defined": len(ruleset.conditions), "matches": matches_count,
        "mismatches_or_errors_in_rules": mismatches_count, "faults_without_highlights": faults_without_highlights
    }

    processed_image_full_url = None
    processed_image_path_str = None
    try:
        output_image_path = settings.UPLOADS_DIR / f"processed_{analysis_id}.png"
        await image_utils.draw_bounding_boxes_on_image(image_path, highlights, output_image_path)
        stored_image_path = await file_processing.store_processed_image(output_image_path, str(analysis_id))
        
        relative_image_path = str(stored_image_path.relative_to(settings.STATIC_SERVED_DIR)).replace('\\', '/')
        processed_image_path_str = relative_image_path
        
        base_url = "http://localhost:8000" 
        processed_image_full_url = f"{base_url}/static/{relative_image_path}"
        
        await file_processing.cleanup_temp_file(output_image_path)
    except Exception as e:
        logger.error(f"Could not generate or save highlighted image for analysis {analysis_id}: {e}", exc_info=True)

    result_object = api_schemas.LabelAnalysisResult(
        analysis_id=analysis_id,
        original_filename=original_filename,
        overall_status=overall_status,
        summary=summary,
        highlights=highlights,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        processed_image_url=processed_image_full_url
    )

    try:
        await crud_analysis.create_analysis(
            result_data=result_object, initial_ruleset=ruleset,
            processed_image_path=processed_image_path_str
        )
        logger.info(f"Successfully saved analysis result {analysis_id} to database.")
    except Exception as e:
        logger.error(f"Failed to save analysis result {analysis_id} to database: {e}", exc_info=True)

    return result_object