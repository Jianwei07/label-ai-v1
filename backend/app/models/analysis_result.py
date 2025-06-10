import sqlalchemy
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID # Using postgresql for robust UUID, works with sqlite
import uuid
from datetime import datetime
import enum

# A central place for your database metadata
metadata = sqlalchemy.MetaData()

# Enum for user feedback status
class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CORRECTED = "corrected"

analysis_results = sqlalchemy.Table(
    "analysis_results",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("original_filename", String, nullable=False),
    Column("overall_status", String, nullable=False),
    
    # Store the complex summary and highlights data as JSON
    Column("summary", JSON, nullable=False),
    Column("highlights", JSON, nullable=False),

    # Path to the visual evidence
    Column("processed_image_path", String, nullable=True),
    
    Column("timestamp", DateTime, default=datetime.utcnow, nullable=False),

    # --- NEW COLUMNS FOR AI IMPROVEMENT ---

    # Store the full RuleSet as parsed by the AI from the .docx file
    Column("initial_ruleset", JSON, nullable=True),
    
    # Track user feedback on the quality of the .docx parsing
    Column("feedback_status", SQLAlchemyEnum(FeedbackStatus), nullable=False, default=FeedbackStatus.PENDING),
    
    # Store a user-corrected version of the RuleSet if feedback is 'corrected'
    Column("corrected_ruleset", JSON, nullable=True),
)
