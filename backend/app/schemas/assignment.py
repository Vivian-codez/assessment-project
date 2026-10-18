"""Assignment schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    course_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: float = 100.0
    rubric_id: Optional[str] = None
    reference_assignment_text: Optional[str] = None


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: float
    rubric_id: Optional[str] = None
    reference_assignment_text: Optional[str] = None
    created_at: datetime
