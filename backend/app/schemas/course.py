"""Course schemas matching frontend structure."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CourseCreate(BaseModel):
    name: str
    code: str
    section: str = "A"
    tone: str = "lav"  # lav, blue, sage, amber
    students_count: int = 0


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    section: Optional[str] = None
    tone: Optional[str] = None
    students_count: Optional[int] = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    code: str
    section: str
    tone: str
    students: int = 0
    students_count: int = 0
    assignments: int = 0
    assignments_count: int = 0
    reviews: int = 0
    reviews_count: int = 0
    flags: int = 0
    flags_count: int = 0


class CourseDetailResponse(CourseResponse):
    health: str = "On track"
    next_deadline: str = "18 October 2024"
    average_score: float = 78.0
