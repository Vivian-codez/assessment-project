# Module docstring explaining that this file defines classroom and student roll-call schemas
"""Classroom and Student roll-call schemas for Supabase educator workflow."""

# Import typing utilities for lists, optional values, and generic dictionary mappings
from typing import List, Optional, Dict, Any
# Import Pydantic base model, field helper, configuration dictionary, and validator
from pydantic import BaseModel, Field, ConfigDict, model_validator
# Import VerismBaseModel base class supporting dual camelCase and snake_case keys
from app.schemas.base import VerismBaseModel


# Schema representing an individual student entry parsed from CSV or manual entry
class StudentItem(VerismBaseModel):
    # Unique student registration or roll number
    roll_number: str
    # Full legal or enrolled name of the student
    full_name: str
    # Optional institutional email address for the student
    email: Optional[str] = None


# Schema for returning student details in API responses
class StudentResponse(VerismBaseModel):
    # Unique string identifier for the student record
    id: str
    # Identifier of the classroom to which the student is enrolled
    classroom_id: str
    # Enrolled roll number or student ID
    roll_number: str
    # Full name of the student
    full_name: str
    # Short name alias for UI display
    name: Optional[str] = None
    # Short roll alias for UI display
    roll: Optional[str] = None
    # Optional email address of the student
    email: Optional[str] = None
    # ISO-formatted timestamp string indicating when the student was added
    created_at: Optional[str] = None

    # Model validator synchronizing name/full_name and roll/roll_number
    @model_validator(mode="after")
    def populate_aliases(self) -> "StudentResponse":
        # Synchronize name with full_name
        if not self.name and self.full_name:
            self.name = self.full_name
        # Synchronize roll with roll_number
        if not self.roll and self.roll_number:
            self.roll = self.roll_number
        # Return validated self instance
        return self


# Schema for returning the summary report after a CSV student roster bulk upload
class StudentUploadCSVResponse(VerismBaseModel):
    # Total count of new student records successfully inserted into the database
    total_inserted: int = 0
    # Total count of duplicate or invalid student rows skipped during upload
    total_skipped: int = 0
    # List of detailed dictionaries describing any skipped rows and error reasons
    skipped: List[Dict[str, Any]] = []
    # List of successfully parsed and inserted student record dictionaries
    inserted: List[Dict[str, Any]] = []
    # File name of the uploaded roster file
    filename: Optional[str] = None
    # Synonymous file_name key
    file_name: Optional[str] = None
    # MIME type of the uploaded roster file
    mime_type: Optional[str] = None
    # Synonymous mimeType key
    mimeType: Optional[str] = None


# Schema for validating classroom creation request bodies
class ClassroomCreate(BaseModel):
    # Display name of the classroom or section
    name: str
    # Unique alphanumeric course or classroom code
    code: str


# Schema for returning classroom details in API responses
class ClassroomResponse(VerismBaseModel):
    # Unique string identifier for the classroom
    id: str
    # Display name of the classroom
    name: str
    # Alphanumeric course/classroom identifier code
    code: str
    # Optional identifier of the instructor managing this classroom
    instructor_id: Optional[str] = None
    # Aggregate count of enrolled students in this classroom, defaulting to 0
    students_count: int = 0
    # ISO-formatted timestamp string indicating when the classroom was created
    created_at: Optional[str] = None
