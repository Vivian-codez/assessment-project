# Module docstring explaining that this file defines course schemas matching the frontend UI requirements
"""Course schemas matching frontend structure."""

# Import Optional type hint for fields that may be omitted
from typing import Optional
# Import Pydantic base model, field helper, and configuration dictionary
from pydantic import BaseModel, Field, ConfigDict
# Import VerismBaseModel base class supporting dual camelCase and snake_case keys
from app.schemas.base import VerismBaseModel


# Schema for validating incoming requests to create a new course
class CourseCreate(BaseModel):
    # Name of the course (e.g. Introduction to Computer Systems)
    name: str
    # Course code abbreviation (e.g. CS101)
    code: str
    # Section or cohort identifier, defaulting to 'A'
    section: str = "A"
    # Visual color tone for UI styling cards (e.g., lav, blue, sage, amber)
    tone: str = "lav"  # lav, blue, sage, amber
    # Initial count of enrolled students, defaulting to 0
    students_count: int = 0


# Schema for validating incoming requests to update an existing course
class CourseUpdate(BaseModel):
    # Optional updated name of the course
    name: Optional[str] = None
    # Optional updated course code
    code: Optional[str] = None
    # Optional updated section identifier
    section: Optional[str] = None
    # Optional updated UI color theme
    tone: Optional[str] = None
    # Optional updated student count
    students_count: Optional[int] = None


# Schema for returning summary information about a course
class CourseResponse(VerismBaseModel):
    # Unique string identifier for the course
    id: str
    # Full name of the course
    name: str
    # Official course code
    code: str
    # Section identifier for this class offering
    section: str = "A"
    # Color tone string assigned for UI card themes
    tone: str = "lav"
    # Student count alias for UI compatibility, defaulting to 0
    students: int = 0
    # Canonical student count attribute, defaulting to 0
    students_count: int = 0
    # Assignment count alias for UI compatibility, defaulting to 0
    assignments: int = 0
    # Canonical assignment count attribute, defaulting to 0
    assignments_count: int = 0
    # Review count alias for UI compatibility, defaulting to 0
    reviews: int = 0
    # Canonical pending review count attribute, defaulting to 0
    reviews_count: int = 0
    # Flagged submission count alias for UI compatibility, defaulting to 0
    flags: int = 0
    # Canonical flagged submission count attribute, defaulting to 0
    flags_count: int = 0
    # Average score across course submissions, defaulting to 0.0
    average_score: float = 0.0


# Schema providing expanded metrics and detailed telemetry for a specific course
class CourseDetailResponse(CourseResponse):
    # High-level operational health assessment text for the course
    health: str = "On track"
    # Human-readable label indicating the upcoming assignment deadline
    next_deadline: Optional[str] = None
    # Mean grade percentage across all graded assignments in this course
    average_score: float = 0.0
