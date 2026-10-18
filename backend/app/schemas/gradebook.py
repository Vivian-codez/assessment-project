"""Gradebook schemas."""

from typing import List, Optional
from pydantic import BaseModel


class GradebookEntryResponse(BaseModel):
    id: str
    name: str  # Student name (decrypted for instructor console)
    roll: str
    a1: float = 0.0
    a2: float = 0.0
    quiz: float = 0.0
    assessment: float = 0.0
    final: float = 0.0
    status: str = "Pending"  # Pending, Reviewed, Approved


class GradebookResponse(BaseModel):
    course_id: str
    course_name: str
    section: str
    students: List[GradebookEntryResponse]
