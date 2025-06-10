import logging
import json
import yaml
import re
from io import BytesIO
from pathlib import Path
from typing import Union, Dict, Any, Optional, List

# Import for reading .docx files
import docx
from pydantic import ValidationError

from app.core.config import settings
from app.api.v1 import schemas as api_schemas
from app.utils.custom_exceptions import PDFParsingError as RuleParsingError # Alias for clarity

logger = logging.getLogger(settings.APP_NAME)


# --- .docx Parsing Logic (Corrected) ---

def _parse_docx_table_row(row_cells: List[str], panel_context: str) -> List[api_schemas.RuleCondition]:
    """
    (CORRECTED) Interprets a single row from a DOCX table into a list of RuleConditions.
    This version is more flexible about where rules and exact text are located.
    """
    conditions = []
    
    # Filter out empty strings from the list of cells
    non_empty_cells = [cell.strip() for cell in row_cells if cell.strip()]
    
    if len(non_empty_cells) < 2:
        # A valid rule row must have at least a target element and exact text/a rule.
        return conditions

    # --- New, more robust logic ---
    target_element_desc = non_empty_cells[0]
    exact_text = non_empty_cells[-1] # Assume the last non-empty cell is the exact text
    
    # Combine all intermediate cells into a single string of raw rules
    raw_rules_text = ", ".join(non_empty_cells[1:-1])

    # Heuristic: Sometimes, the last cell is also a rule, not "exact text".
    # If the last cell contains common rule keywords, treat it as part of the rules.
    rule_keywords = ['font', 'height', 'width', 'placement', 'mandatory', 'box', 'mm', '≥', '≤']
    if any(keyword in exact_text.lower() for keyword in rule_keywords):
        # The last cell seems to be a rule, not exact text.
        raw_rules_text = ", ".join(non_empty_cells[1:])
        exact_text = None # There is no exact text to check for this row.
    
    # --- Rule Generation ---

    # Create a rule for the exact text if it exists
    if exact_text:
        conditions.append(api_schemas.RuleCondition(
            type=api_schemas.RuleType.EXACT_TEXT_MATCH,
            description=f"Check for exact text of '{target_element_desc}' on panel '{panel_context}'",
            target_element_description=target_element_desc,
            expected_text=exact_text
        ))

    # Parse the raw rules text for specific rule patterns using regex
    if raw_rules_text:
        # Pattern for font size: "Font height: [operator] [value]mm"
        font_size_match = re.search(r'Font height:\s*(≥|>|=|<|≤)\s*(\d+\.?\d*)\s*mm', raw_rules_text, re.IGNORECASE)
        if font_size_match:
            op_symbol = font_size_match.group(1)
            op_map = { '≥': 'min', '>': 'min', '=': 'exactly', '<': 'max', '≤': 'max' }
            conditions.append(api_schemas.RuleCondition(
                type=api_schemas.RuleType.FONT_SIZE,
                description=f"Check font size of '{target_element_desc}'",
                target_element_description=target_element_desc,
                font_size_operator=op_map.get(op_symbol, 'exactly'),
                font_size_value=float(font_size_match.group(2)),
                font_size_unit='mm'
            ))

        # Pattern for barcode width: "Width = [value]mm"
        barcode_width_match = re.search(r'Width\s*=\s*(\d+\.?\d*)\s*mm', raw_rules_text, re.IGNORECASE)
        if barcode_width_match:
            conditions.append(api_schemas.RuleCondition(
                type=api_schemas.RuleType.BARCODE_DIMENSIONS,
                description=f"Check width of '{target_element_desc}'",
                target_element_description=target_element_desc,
                expected_width_mm=float(barcode_width_match.group(1))
            ))
            
        # Pattern for barcode height: "Height = [value]mm"
        barcode_height_match = re.search(r'Height\s*=\s*(\d+\.?\d*)\s*mm', raw_rules_text, re.IGNORECASE)
        if barcode_height_match:
            # We will merge this with an existing barcode rule if one was created for width
            existing_barcode_rule = next((c for c in conditions if c.type == api_schemas.RuleType.BARCODE_DIMENSIONS and c.target_element_description == target_element_desc), None)
            if existing_barcode_rule:
                existing_barcode_rule.expected_height_mm = float(barcode_height_match.group(1))
            else:
                 conditions.append(api_schemas.RuleCondition(
                    type=api_schemas.RuleType.BARCODE_DIMENSIONS,
                    description=f"Check height of '{target_element_desc}'",
                    target_element_description=target_element_desc,
                    expected_height_mm=float(barcode_height_match.group(1))
                ))

    return conditions


async def _parse_docx(file_content: bytes) -> Optional[api_schemas.RuleSet]:
    """Parses a .docx file containing rules in tables."""
    try:
        document = docx.Document(BytesIO(file_content))
        all_conditions = []
        current_panel_context = "Unknown Panel"

        for table in document.tables:
            # Simple heuristic to skip header-like tables (e.g., PRODUCT INFORMATION table)
            if len(table.rows) > 0 and len(table.rows[0].cells) < 3:
                continue

            for row in table.rows:
                row_texts = [cell.text for cell in row.cells]
                
                # Skip header rows
                if "Labelling Rules" in row_texts[0]:
                    continue

                # Heuristic to find panel context headers (e.g., "Front Panel")
                # Assumes they are in the first cell and other cells in that row are empty/merged.
                cleaned_row_texts = [cell.strip() for cell in row_texts if cell.strip()]
                if len(cleaned_row_texts) == 1 and cleaned_row_texts[0].lower().endswith('panel'):
                    current_panel_context = cleaned_row_texts[0]
                    logger.info(f"Switched to panel context: {current_panel_context}")
                    continue

                # Parse the row for rules
                parsed_conditions = _parse_docx_table_row(row_texts, current_panel_context)
                if parsed_conditions:
                    all_conditions.extend(parsed_conditions)
        
        if not all_conditions:
            # This is the error you received. It means the loop finished with no rules found.
            raise RuleParsingError("No valid rule conditions could be extracted from the DOCX file tables.")

        return api_schemas.RuleSet(
            name="Rules extracted from DOCX",
            description="Automatically parsed from the uploaded Word document.",
            conditions=all_conditions
        )

    except Exception as e:
        logger.error(f"Failed to process DOCX file: {e}", exc_info=True)
        # Re-raise as our specific exception type so the API can handle it gracefully
        if isinstance(e, RuleParsingError):
            raise
        raise RuleParsingError(f"Error reading or parsing the .docx file: {e}")


# --- Main Service Function ---
async def parse_rules_from_content(
    file_content: bytes,
    filename: str
) -> Optional[api_schemas.RuleSet]:
    """
    Parses rule definitions from file content (JSON, YAML, or DOCX).
    """
    logger.info(f"Parsing rules from content of file: {filename}")
    
    if not filename:
        raise RuleParsingError("Filename is required to determine rule file format.")

    try:
        file_suffix = Path(filename).suffix.lower()

        if file_suffix == ".docx":
            return await _parse_docx(file_content)

        decoded_content = file_content.decode('utf-8')

        if file_suffix == ".json":
            rules_dict = json.loads(decoded_content)
        elif file_suffix in [".yaml", ".yml"]:
            rules_dict = yaml.safe_load(decoded_content)
        else:
            raise RuleParsingError(f"Unsupported rule file format: {file_suffix}.")

        parsed_ruleset = api_schemas.RuleSet.model_validate(rules_dict)
        logger.info(f"Successfully parsed and validated RuleSet '{parsed_ruleset.name}' from '{filename}'.")
        return parsed_ruleset

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise RuleParsingError(f"Invalid format in '{filename}': {e}")
    except ValidationError as e:
        raise RuleParsingError(f"Invalid RuleSet structure in '{filename}': {e.errors()}")
    except UnicodeDecodeError as e:
        raise RuleParsingError(f"Encoding error in '{filename}': ensure it's UTF-8 encoded.")
    except RuleParsingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing rules from '{filename}': {e}", exc_info=True)
        raise RuleParsingError(f"An unexpected error occurred while parsing rules from '{filename}'.")
