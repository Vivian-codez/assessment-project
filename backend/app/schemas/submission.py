"""Submission schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SubmissionCreate(BaseModel):
    assignment_id: Optional[str] = None
    student_name: str
    student_roll: str
    student_email: Optional[str] = None
    extracted_text: Optional[str] = None


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    assignment_id: str
    student: str  # Decrypted student name
    roll: str     # Decrypted roll
    file_name: str
    status: str
    score: float = 0.0
    similarity: float = 0.0
    ai_content: float = Field(default=0.0, alias="aiContent")
    web_plagiarism: float = Field(default=0.0, alias="webPlagiarism")
    file_url: Optional[str] = None
    created_at: datetime


class SubmissionDetailResponse(SubmissionResponse):
    extracted_text: Optional[str] = None
    content: Optional[str] = None
    matching_phrase: Optional[str] = None
    criteria_scores: List[dict] = Field(default_factory=list)
    ai_feedback: Optional[str] = None
    teacher_feedback: Optional[str] = None
    web_sources: List[dict] = Field(default_factory=list, alias="webSources")
    plagiarised_words: List[str] = Field(default_factory=list, alias="plagiarisedWords")


class BatchUploadResponse(BaseModel):
    batch_id: str
    total_files: int
    uploaded_files: List[str]
    submissions: List[SubmissionResponse]
