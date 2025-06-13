from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import List, Optional, Dict, Any, Union, Literal
from uuid import UUID, uuid4
from enum import Enum

# --- General Purpose Schemas ---
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str

class ErrorDetailItem(BaseModel):
    """Structure for individual error details, useful for validation errors."""
    loc: Optional[List[str | int]] = None
    msg: str
    type: str

class ErrorResponse(BaseModel):
    """Standard error response structure."""
    detail: Union[str, List[ErrorDetailItem]]
    error_code: Optional[str] = None


# --- Rule Definition Schemas ---
class RuleType(str, Enum):
    """Enumeration for different types of rules that can be defined."""
    EXACT_TEXT_MATCH = "exact_text_match"
    FONT_SIZE = "font_size"
    SPACING = "spacing" # Could be between words, lines, or elements
    BARCODE_DIMENSIONS = "barcode_dimensions"
    ELEMENT_PRESENCE = "element_presence"
    TRANSLATION_MATCH = "translation_match"
    # Add more specific rule types as needed

class ComparisonOperator(str, Enum):
    """Comparison operators for rules like font size or dimensions."""
    EXACTLY = "exactly"
    MIN = "min" # minimum
    MAX = "max" # maximum
    BETWEEN = "between"

class RuleCondition(BaseModel):
    """Defines a specific condition to check."""
    type: RuleType = Field(..., description="The type of check to perform.")
    description: Optional[str] = Field(None, description="Human-readable description of the rule.")
    target_element_description: Optional[str] = Field(None, description="Description of the element on the label this rule applies to (e.g., 'Ingredient List Header', 'Net Weight Text'). Helps locate the element if not using coordinates.")
    
    # Fields for EXACT_TEXT_MATCH / TRANSLATION_MATCH
    expected_text: Optional[str] = Field(None, description="The exact text string expected.")
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'fr') for the text, useful for translation checks.")
    case_sensitive: Optional[bool] = Field(True, description="Whether text matching should be case sensitive.")

    # Fields for FONT_SIZE
    font_size_value: Optional[float] = Field(None, description="The font size value (e.g., 3 for 3mm).")
    font_size_unit: Optional[Literal["mm", "pt", "px"]] = Field(None, description="Unit for font size.")
    font_size_operator: Optional[ComparisonOperator] = Field(ComparisonOperator.EXACTLY, description="Operator for font size comparison.")
    font_size_value_upper: Optional[float] = Field(None, description="Upper bound for font size if operator is 'between'.") # For 'between'

    # Fields for ELEMENT_PRESENCE
    is_present: Optional[bool] = Field(True, description="Whether the element is expected to be present or absent.")

    # Fields for BARCODE_DIMENSIONS / SPACING (examples, can be more detailed)
    expected_width_mm: Optional[float] = None
    expected_height_mm: Optional[float] = None
    tolerance_mm: Optional[float] = Field(0.5, description="Tolerance in mm for dimension checks.")
    
    # Optional: Coordinates for a reference area if the rule applies to a specific region
    # target_roi: Optional[List[int]] = Field(None, description="Region of Interest [x, y, width, height] on the label for this rule. If not provided, system will try to locate based on target_element_description.")

    # Optional: Sensitivity for this specific rule, overrides global if set
    sensitivity_override: Optional[int] = Field(None, ge=0, le=100, description="Rule-specific sensitivity (0-100).")

    @field_validator("font_size_operator")
    def check_font_size_upper_value(cls, v, values):
        if v == ComparisonOperator.BETWEEN and values.data.get("font_size_value_upper") is None:
            raise ValueError("font_size_value_upper is required when operator is 'between'")
        return v


class RuleSet(BaseModel):
    """A collection of rules to be applied to a label."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="A descriptive name for this set of rules.")
    description: Optional[str] = Field(None, description="Optional detailed description of the rule set.")
    conditions: List[RuleCondition] = Field(..., description="List of individual rule conditions.")


# --- Label Analysis Schemas ---
class BoundingBox(BaseModel):
    """Defines a bounding box with coordinates."""
    x: int = Field(..., description="X-coordinate of the top-left corner.")
    y: int = Field(..., description="Y-coordinate of the top-left corner.")
    width: int = Field(..., description="Width of the bounding box.")
    height: int = Field(..., description="Height of the bounding box.")

class HighlightedElement(BaseModel):
    """Information about a highlighted element on the label."""
    rule_id_ref: Optional[str] = Field(None, description="Reference to the specific rule ID that this highlight pertains to (if applicable).") # Could be an index or a specific ID from RuleCondition
    bounding_box: BoundingBox = Field(..., description="Coordinates of the highlight on the image.")
    status: Literal["correct", "wrong", "info"] = Field(..., description="Status of the checked element.")
    message: str = Field(..., description="Tooltip message explaining why it's correct or wrong.")
    found_value: Optional[str] = Field(None, description="The actual value found by the checker (e.g., '2.8mm', 'Ingredient Listt').")
    expected_value: Optional[str] = Field(None, description="The value expected by the rule.")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score of the detection/check, if applicable.")

class LabelAnalysisRequest(BaseModel):
    """Request model for initiating a label analysis."""
    # The label image will be sent as a file upload, not in JSON body.
    # The rules can be sent as JSON or as a file upload (YAML/JSON).
    rules_json: Optional[RuleSet] = Field(None, description="RuleSet provided as a JSON object.")
    # rules_file_id: Optional[str] = Field(None, description="ID of a previously uploaded rules file (YAML/JSON).") # Alternative to sending rules_json
    sensitivity: Optional[int] = Field(50, ge=0, le=100, description="Global sensitivity for checking (0-100). Low for essentials, High for precise details.")

class LabelAnalysisResult(BaseModel):
    """Response model for label analysis results."""
    analysis_id: UUID = Field(default_factory=uuid4)
    original_filename: str = Field(..., description="Filename of the uploaded label image.")
    overall_status: Literal["pass", "fail_critical", "fail_minor", "processing_error"] = Field(..., description="Overall outcome of the analysis.")
    summary: Dict[str, Any] = Field(..., description="Summary statistics (e.g., total rules, matches, mismatches).")
    highlights: List[HighlightedElement] = Field(..., description="List of elements to be highlighted on the label image.")
    # Optional: URL to a processed image with highlights drawn (if backend generates this)
    # processed_image_url: Optional[HttpUrl] = None
    timestamp: str # ISO format timestamp

# --- For File Uploads (used by FastAPI, not directly in JSON body) ---
# No specific Pydantic model needed here for UploadFile, FastAPI handles it.

# --- Rule Management Schemas (if you build a CRUD for rules) ---
class RuleSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: List[RuleCondition]

class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[RuleCondition]] = None

class RuleSetInDB(RuleSet):
    # Potentially add created_at, updated_at fields if storing in DB
    pass

# --- ADDED THIS FIELD ---
    processed_image_url: Optional[HttpUrl] = Field(None, description="URL to the label image with highlights drawn on it.")