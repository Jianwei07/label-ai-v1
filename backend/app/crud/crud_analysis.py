import json
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, insert, update
from pydantic import ValidationError

from app.db.session import database
from app.models.analysis_result import analysis_results, FeedbackStatus
from app.api.v1 import schemas as api_schemas
from app.utils.custom_exceptions import DatabaseError

async def create_analysis(
    result_data: api_schemas.LabelAnalysisResult,
    initial_ruleset: api_schemas.RuleSet,
    processed_image_path: Optional[str] = None
) -> None:
    """
    Saves a completed analysis result, including the initial AI-parsed ruleset, to the database.
    """
    try:
        # Pydantic models need to be converted to JSON-compatible dicts for the DB
        values = {
            "id": result_data.analysis_id,
            "original_filename": result_data.original_filename,
            "overall_status": result_data.overall_status,
            "summary": result_data.summary,
            "highlights": [h.model_dump() for h in result_data.highlights],
            "processed_image_path": processed_image_path,
             "timestamp": datetime.fromisoformat(result_data.timestamp),
            # Add the new fields for AI improvement
            "initial_ruleset": json.loads(initial_ruleset.model_dump_json()),
            "feedback_status": FeedbackStatus.PENDING, # Default status
            "corrected_ruleset": None, # No correction initially
        }
        query = insert(analysis_results).values(**values)
        await database.execute(query)
    except Exception as e:
        raise DatabaseError(f"Error saving analysis result to database: {e}")


async def get_analysis(analysis_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single analysis result from the database by its ID.
    """
    try:
        query = select(analysis_results).where(analysis_results.c.id == analysis_id)
        result = await database.fetch_one(query)
        if result:
            return dict(result._mapping)
        return None
    except Exception as e:
        raise DatabaseError(f"Error retrieving analysis result from database: {e}")


async def get_all_analyses(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves a list of all analysis results, with pagination.
    """
    try:
        # Order by timestamp descending to get the most recent results first
        query = select(analysis_results).order_by(analysis_results.c.timestamp.desc()).offset(skip).limit(limit)
        results = await database.fetch_all(query)
        return [dict(result._mapping) for result in results]
    except Exception as e:
        raise DatabaseError(f"Error retrieving all analysis results from database: {e}")

async def update_analysis_feedback(
    analysis_id: UUID, 
    feedback_status: FeedbackStatus, 
    corrected_ruleset: Optional[api_schemas.RuleSet] = None
) -> None:
    """
    (For Future Use) Updates an analysis result with user feedback.
    """
    try:
        values = {
            "feedback_status": feedback_status,
            "corrected_ruleset": corrected_ruleset.model_dump() if corrected_ruleset else None
        }
        query = (
            update(analysis_results)
            .where(analysis_results.c.id == analysis_id)
            .values(**values)
        )
        await database.execute(query)
    except Exception as e:
        raise DatabaseError(f"Error updating feedback for analysis {analysis_id}: {e}")

