# Module docstring explaining that this file defines schemas for batch job execution and status tracking
"""Batch job execution and progress schemas."""

# Import typing utilities for lists and optional values
from typing import List, Optional
# Import Pydantic base model, field constructor, and configuration dictionary
from pydantic import BaseModel, Field, ConfigDict


# Schema for validating incoming requests to trigger a batch evaluation background job
class BatchEvaluationRequest(BaseModel):
    # Optional identifier of the assignment to evaluate submissions for
    assignment_id: Optional[str] = None
    # Optional list of specific submission IDs to evaluate, defaulting to None (all pending)
    submission_ids: Optional[List[str]] = None  # None means evaluate all pending for the assignment
    # Optional rubric ID to apply during grading evaluation
    rubric_id: Optional[str] = None
    # Percentage threshold above which submissions are flagged for peer similarity, defaulting to 90.0
    similarity_threshold: float = 90.0
    # Optional human-readable title or label for the batch evaluation task
    title: Optional[str] = None
    # Optional reference exemplar solution text used by the AI evaluator
    reference_assignment_text: Optional[str] = None


# Schema for returning detailed batch job progress in API responses
class BatchJobResponse(BaseModel):
    # Configure model to support field aliases and ORM attribute reading
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    # Unique string identifier of the background batch job
    job_id: str
    # Execution lifecycle status (e.g., queued, processing, completed, failed)
    status: str  # queued, processing, completed, failed
    # Overall percentage of job completion, mapping to progress_pct field
    progress: float = Field(alias="progress_pct", default=0.0)
    # Total count of items scheduled for processing, mapping to total_items field
    total: int = Field(alias="total_items", default=0)
    # Number of items successfully processed so far, mapping to processed_items field
    processed: int = Field(alias="processed_items", default=0)
    # Count of submissions flagged for high similarity during processing
    similarity_flags: int = 0
    # Count of graded submissions ready for instructor review
    ready_for_review: int = 0
    # Detailed error description if the job encountered a failure
    error_message: Optional[str] = None


# Schema for lightweight polling of background task progress
class JobStatusResponse(BaseModel):
    # Unique identifier of the batch job being polled
    batch_job_id: str
    # Current status state string (e.g., PENDING, PROCESSING, SUCCESS, FAILURE)
    status: str  # PENDING, PROCESSING, SUCCESS, FAILURE
    # Number of items completed so far
    current: int = 0
    # Total number of items in the job
    total: int = 0
    # Computed percentage completion from 0.0 to 100.0
    percent: float = 0.0
    # Optional dictionary containing final task results upon success
    result: Optional[dict] = None
    # Optional error message string if the task failed
    error: Optional[str] = None

