"""Pydantic schemas for multi-tenant assignment evaluation pipeline."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# Gemini Evaluation Output Schema (Enforced via Gemini response_schema)
class EvaluationOutput(BaseModel):
    """Structured evaluation output returned by Gemini API."""
    model_config = ConfigDict(extra="ignore")

    score: float = Field(
        ...,
        description="Overall percentage or numeric evaluation score (0.0 to 100.0) based on rubric criteria.",
        ge=0.0,
        le=100.0,
    )
    criteria_breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Granular assessment mapping rubric criteria names to score and comments.",
    )
    feedback: str = Field(
        ...,
        description="Comprehensive constructive qualitative feedback and critique for the student.",
    )
    improvement_areas: List[str] = Field(
        default_factory=list,
        description="List of specific, actionable recommendations and areas for student improvement.",
    )


# Assignment Folder Schemas
class AssignmentFolderCreate(BaseModel):
    """Payload to create a new assignment folder."""
    title: str = Field(..., min_length=1, max_length=255, description="Folder title or assignment name")
    rubric_text: str = Field(..., min_length=1, description="Grading criteria and rubric instructions")


class AssignmentFolderUpdate(BaseModel):
    """Payload to update an existing assignment folder."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    rubric_text: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, pattern="^(pending|processing|completed)$")


# Evaluation Result Schema
class EvaluationResultResponse(BaseModel):
    """Schema representing an evaluation result record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    score: float
    feedback_json: Dict[str, Any]
    evaluated_at: datetime


# Submission Schemas
class FolderSubmissionCreate(BaseModel):
    """Payload to add a student submission to an assignment folder."""
    student_identifier: str = Field(..., min_length=1, max_length=255, description="Student roll number or ID")
    extracted_text: str = Field(..., min_length=1, description="Raw or parsed student submission content")
    file_path: Optional[str] = Field(None, description="Optional path to submission file on disk")


class FolderSubmissionResponse(BaseModel):
    """Schema representing a student submission inside an assignment folder."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    folder_id: Optional[str] = None
    student_identifier: Optional[str] = None
    file_path: Optional[str] = None
    extracted_text: Optional[str] = None
    evaluation_status: str
    created_at: datetime
    evaluation: Optional[EvaluationResultResponse] = None


class AssignmentFolderResponse(BaseModel):
    """Response schema for assignment folder with metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    rubric_text: str
    status: str
    created_at: datetime
    submission_count: int = 0
    submissions: Optional[List[FolderSubmissionResponse]] = None


# Monthly Usage Schemas
class MonthlyUsageResponse(BaseModel):
    """Response schema for tenant monthly quota and token consumption."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    billing_month: str
    submissions_evaluated: int
    token_count: int
    quota_limit: int = 100
    remaining_quota: int = 100


# Endpoint Evaluation Trigger Response Schema
class EvaluateFolderResponse(BaseModel):
    """Structured response returned when triggering folder evaluation."""
    status: str = Field(..., description="'processing', 'quota_deferred', or 'completed'")
    folder_id: str
    queued_submissions: int = Field(0, description="Count of submissions queued for grading")
    deferred_submissions: int = Field(0, description="Count of submissions deferred due to quota limits")
    message: Optional[str] = None

