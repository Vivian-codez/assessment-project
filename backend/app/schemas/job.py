"""Batch job execution and progress schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BatchEvaluationRequest(BaseModel):
    assignment_id: Optional[str] = None
    submission_ids: Optional[List[str]] = None  # None means evaluate all pending for the assignment
    rubric_id: Optional[str] = None
    similarity_threshold: float = 90.0
    title: Optional[str] = None
    reference_assignment_text: Optional[str] = None


class BatchJobResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    job_id: str
    status: str  # queued, processing, completed, failed
    progress: float = Field(alias="progress_pct", default=0.0)
    total: int = Field(alias="total_items", default=0)
    processed: int = Field(alias="processed_items", default=0)
    similarity_flags: int = 0
    ready_for_review: int = 0
    error_message: Optional[str] = None
