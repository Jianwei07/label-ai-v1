import logging
from pathlib import Path
from uuid import UUID
from typing import List, Dict, Any
import datetime

from app.core.config import settings
from app.api.v1 import schemas as api_schemas
from app.services import ocr, visual_analysis
from app.utils import text_utils
from app.utils.custom_exceptions import RuleEngineError

logger = logging.getLogger(settings.APP_NAME)

async def process_label_analysis_sync(
    analysis_id: UUID,
    image_path: Path,
    ruleset: api_schemas.RuleSet,
    sensitivity: int,
    original_filename: str
) -> api_schemas.LabelAnalysisResult:
    """
    Orchestrates the entire label analysis process based on a structured RuleSet.
    """
    logger.info(f"Starting analysis (ID: {analysis_id}) for image: {image_path.name}")
    
    highlights: List[api_schemas.HighlightedElement] = []
    matches_count = 0
    mismatches_count = 0

    # --- Pre-computation Step ---
    # Perform OCR and barcode detection once to avoid re-reading the image for every rule.
    all_ocr_data = await ocr.extract_text_from_image(image_path)
    detected_barcodes = await visual_analysis.detect_and_measure_barcode(image_path)

    # --- Rule Execution Step ---
    for i, condition in enumerate(ruleset.conditions):
        rule_id_ref = f"rule_{i+1}_{condition.type.value}"
        
        try:
            if condition.type == api_schemas.RuleType.EXACT_TEXT_MATCH:
                # Find the text in OCR data and create a highlight
                found_match = False
                for ocr_item in all_ocr_data:
                    if text_utils.compare_text_exactly(ocr_item.text, condition.expected_text):
                        highlights.append(api_schemas.HighlightedElement(
                            rule_id_ref=rule_id_ref,
                            bounding_box=api_schemas.BoundingBox(x=ocr_item.left, y=ocr_item.top, width=ocr_item.width, height=ocr_item.height),
                            status="correct",
                            message=f"Found expected text: '{condition.expected_text}'",
                            found_value=ocr_item.text,
                            expected_value=condition.expected_text,
                        ))
                        matches_count += 1
                        found_match = True
                        break # Assume first match is enough
                
                if not found_match:
                    mismatches_count += 1
                    # No highlight can be added for missing text unless a search area is defined.

            elif condition.type == api_schemas.RuleType.FONT_SIZE:
                # Find the target text first, then check its font size
                target_ocr_item = next((item for item in all_ocr_data if text_utils.compare_text_exactly(item.text, condition.target_element_description)), None)
                if not target_ocr_item:
                    # Alternative: search if target_element_description is IN the text
                    target_ocr_item = next((item for item in all_ocr_data if condition.target_element_description in item.text), None)

                if target_ocr_item:
                    # In a real implementation, this would call visual_analysis.measure_font_size
                    # For now, we'll just create a placeholder
                    highlights.append(api_schemas.HighlightedElement(
                        rule_id_ref=rule_id_ref,
                        bounding_box=api_schemas.BoundingBox(x=target_ocr_item.left, y=target_ocr_item.top, width=target_ocr_item.width, height=target_ocr_item.height),
                        status="info", # 'info' because it's a placeholder
                        message=f"Font size check for '{condition.target_element_description}' is not fully implemented.",
                    ))
                    # In a real scenario, you'd increment matches_count or mismatches_count based on the result
                else:
                    mismatches_count += 1
                    logger.warning(f"Could not find target '{condition.target_element_description}' for font size check.")

            elif condition.type == api_schemas.RuleType.BARCODE_DIMENSIONS:
                # Check against pre-detected barcodes
                barcode_to_check = next((bc for bc in detected_barcodes if bc.get("data") == condition.expected_text), None)
                if not barcode_to_check: # If rule doesn't specify barcode data, check first one found
                     if detected_barcodes: barcode_to_check = detected_barcodes[0]
                
                if barcode_to_check:
                    # Compare measured dimensions with expected dimensions from the rule
                    width_ok = abs(barcode_to_check['measured_width_mm'] - (condition.expected_width_mm or 0)) < 1.0 # 1mm tolerance
                    height_ok = abs(barcode_to_check['measured_height_mm'] - (condition.expected_height_mm or 0)) < 1.0
                    
                    status = "correct" if width_ok and height_ok else "wrong"
                    if status == "correct": matches_count += 1
                    else: mismatches_count += 1
                    
                    highlights.append(api_schemas.HighlightedElement(
                        rule_id_ref=rule_id_ref,
                        bounding_box=barcode_to_check['bounding_box'],
                        status=status,
                        message=f"Barcode check. Found: W={barcode_to_check['measured_width_mm']:.2f}mm, H={barcode_to_check['measured_height_mm']:.2f}mm",
                        expected_value=f"W={condition.expected_width_mm}mm, H={condition.expected_height_mm}mm"
                    ))
                else:
                    mismatches_count += 1
                    logger.warning(f"No barcode found to check against rule '{condition.description}'.")

        except Exception as e:
            logger.error(f"Error processing rule '{rule_id_ref}': {e}", exc_info=True)
            mismatches_count += 1

    # --- Construct Final Result ---
    overall_status = "pass" if mismatches_count == 0 else "fail_minor"
    summary = {
        "total_rules_defined": len(ruleset.conditions),
        "matches": matches_count,
        "mismatches_or_errors_in_rules": mismatches_count,
    }

    return api_schemas.LabelAnalysisResult(
        analysis_id=analysis_id,
        original_filename=original_filename,
        overall_status=overall_status,
        summary=summary,
        highlights=highlights,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

