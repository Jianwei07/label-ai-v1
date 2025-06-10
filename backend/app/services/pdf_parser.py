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


# --- .docx Parsing Logic (Corrected & with Debugging) ---

def _parse_docx_table_row(row_cells: List[str], panel_context: str) -> List[api_schemas.RuleCondition]:
    """
    (CORRECTED) Interprets a single row from a DOCX table into a list of RuleConditions.
    """
    conditions = []
    
    non_empty_cells = [cell.strip() for cell in row_cells if cell.strip()]
    
    if len(non_empty_cells) < 2:
        return conditions

    target_element_desc = non_empty_cells[0]
    exact_text = non_empty_cells[-1]
    raw_rules_text = ", ".join(non_empty_cells[1:-1])

    rule_keywords = ['font', 'height', 'width', 'placement', 'mandatory', 'box', 'mm', '≥', '≤']
    if any(keyword in exact_text.lower() for keyword in rule_keywords):
        raw_rules_text = ", ".join(non_empty_cells[1:])
        exact_text = None
    
    if exact_text:
        conditions.append(api_schemas.RuleCondition(
            type=api_schemas.RuleType.EXACT_TEXT_MATCH,
            description=f"Check for exact text of '{target_element_desc}' on panel '{panel_context}'",
            target_element_description=target_element_desc,
            expected_text=exact_text
        ))

    if raw_rules_text:
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

        barcode_width_match = re.search(r'Width\s*=\s*(\d+\.?\d*)\s*mm', raw_rules_text, re.IGNORECASE)
        if barcode_width_match:
            conditions.append(api_schemas.RuleCondition(
                type=api_schemas.RuleType.BARCODE_DIMENSIONS,
                description=f"Check width of '{target_element_desc}'",
                target_element_description=target_element_desc,
                expected_width_mm=float(barcode_width_match.group(1))
            ))
            
        barcode_height_match = re.search(r'Height\s*=\s*(\d+\.?\d*)\s*mm', raw_rules_text, re.IGNORECASE)
        if barcode_height_match:
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

    if conditions:
        logger.debug(f"Successfully parsed {len(conditions)} condition(s) from row starting with '{target_element_desc}'")
    return conditions


async def _parse_docx(file_content: bytes) -> Optional[api_schemas.RuleSet]:
    """Parses a .docx file containing rules in tables."""
    try:
        document = docx.Document(BytesIO(file_content))
        all_conditions = []
        current_panel_context = "Unknown Panel"

        logger.debug(f"Found {len(document.tables)} table(s) in the DOCX file.")

        for i, table in enumerate(document.tables):
            logger.debug(f"Processing Table {i+1} with {len(table.rows)} rows and {len(table.columns)} columns.")

            for j, row in enumerate(table.rows):
                row_texts = [cell.text for cell in row.cells]
                logger.debug(f"Table {i+1}, Row {j+1} RAW content: {row_texts}")

                if not row_texts or not row_texts[0].strip():
                    logger.debug(f"Table {i+1}, Row {j+1} is empty, skipping.")
                    continue
                
                # Log header detection
                if "Labelling Rules" in row_texts[0].strip():
                    logger.debug(f"Table {i+1}, Row {j+1} is a header, skipping.")
                    continue

                cleaned_row_texts = [cell.strip() for cell in row_texts if cell.strip()]
                logger.debug(f"Table {i+1}, Row {j+1} CLEANED content: {cleaned_row_texts}")
                
                # Heuristic to find panel context headers
                if len(cleaned_row_texts) == 1 and cleaned_row_texts[0].lower().endswith(('panel', 'panel (top)', 'panel (nip)', 'panel (bottom)')):
                    current_panel_context = cleaned_row_texts[0]
                    logger.info(f"Switched to panel context: {current_panel_context}")
                    continue

                # Parse the row for rules
                parsed_conditions = _parse_docx_table_row(row_texts, current_panel_context)
                logger.debug(f"Parsed conditions from row: {parsed_conditions}")
                if parsed_conditions:
                    all_conditions.extend(parsed_conditions)
        
        logger.info(f"Total rule conditions extracted from DOCX: {len(all_conditions)}")
        if not all_conditions:
            raise RuleParsingError("No valid rule conditions could be extracted from the DOCX file tables.")

        return api_schemas.RuleSet(
            name="Rules extracted from DOCX",
            description="Automatically parsed from the uploaded Word document.",
            conditions=all_conditions
        )

    except Exception as e:
        logger.error(f"Failed to process DOCX file: {e}", exc_info=True)
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