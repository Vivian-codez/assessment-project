# Module docstring explaining that this file defines gradebook schemas
"""Gradebook schemas."""

# Import typing utilities for lists and optional types
from typing import List, Optional
# Import Pydantic base model class
from pydantic import BaseModel


# Schema representing an individual student's row entry in the course gradebook
class GradebookEntryResponse(BaseModel):
    # Unique string identifier for the student or gradebook row
    id: str
    # Plaintext decrypted student name for display on the instructor console
    name: str  # Student name (decrypted for instructor console)
    # Student roll number or registration ID
    roll: str
    # Score achieved on assignment 1, defaulting to 0.0
    a1: float = 0.0
    # Score achieved on assignment 2, defaulting to 0.0
    a2: float = 0.0
    # Score achieved on quizzes, defaulting to 0.0
    quiz: float = 0.0
    # Score achieved on assessment component, defaulting to 0.0
    assessment: float = 0.0
    # Final aggregate or weighted score, defaulting to 0.0
    final: float = 0.0
    # Current grading status (e.g., Pending, Reviewed, Approved)
    status: str = "Pending"  # Pending, Reviewed, Approved


# Schema representing the full gradebook matrix response for an entire course
class GradebookResponse(BaseModel):
    # Unique identifier of the course
    course_id: str
    # Title or name of the course
    course_name: str
    # Specific section cohort identifier
    section: str
    # List of individual student score entries for this gradebook
    students: List[GradebookEntryResponse]
