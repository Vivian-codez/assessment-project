# Module docstring explaining that this file defines assignment validation schemas
"""Assignment schemas."""

# Import datetime utility for timestamp validation
from datetime import datetime
# Import Optional type hint for fields that can be None
from typing import Optional
# Import Pydantic base model and configuration dictionary for schema definition
from pydantic import BaseModel, ConfigDict


# Schema for validating input payload when creating a new assignment
class AssignmentCreate(BaseModel):
    # Optional identifier of the course to which this assignment belongs
    course_id: Optional[str] = None
    # Mandatory title or name of the assignment
    title: str
    # Optional detailed instructions or description for the assignment
    description: Optional[str] = None
    # Optional deadline timestamp for student submissions
    due_date: Optional[datetime] = None
    # Maximum possible score for this assignment, defaulting to 100.0 points
    max_score: float = 100.0
    # Optional identifier of the rubric associated with this assignment
    rubric_id: Optional[str] = None
    # Optional exemplar or reference solution text used for AI evaluation
    reference_assignment_text: Optional[str] = None


# Schema for returning assignment data in API responses
class AssignmentResponse(BaseModel):
    # Configure model to support reading attributes directly from ORM objects
    model_config = ConfigDict(from_attributes=True)

    # Unique string identifier for the assignment
    id: str
    # String identifier of the course this assignment belongs to
    course_id: str
    # Name or title of the assignment
    title: str
    # Optional instructions or description for the assignment
    description: Optional[str] = None
    # Optional deadline timestamp for student submissions
    due_date: Optional[datetime] = None
    # Maximum achievable score for the assignment
    max_score: float
    # Optional rubric identifier linked to this assignment
    rubric_id: Optional[str] = None
    # Optional exemplar or reference text for grading context
    reference_assignment_text: Optional[str] = None
    # Timestamp indicating when the assignment was created
    created_at: datetime
