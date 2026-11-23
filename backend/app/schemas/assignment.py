# Module docstring explaining that this file defines assignment validation schemas
"""Assignment schemas."""

# Import datetime utility for timestamp validation
from datetime import datetime
# Import Optional type hint for fields that can be None
from typing import Optional
# Import Pydantic base model, field helper, and model validator
from pydantic import BaseModel, ConfigDict, model_validator
# Import VerismBaseModel base class supporting dual camelCase and snake_case keys
from app.schemas.base import VerismBaseModel


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
    # Lifecycle status: Draft, Open, Grading, Reviewed, Published
    status: str = "Draft"
    # Assignment category: homework, exam, lab, project
    assignment_type: str = "homework"
    # Configurable peer-to-peer similarity alert threshold percentage
    similarity_threshold: float = 70.0
    # Optional starter template or boilerplate code
    starter_code: Optional[str] = None


# Schema for updating existing assignments
class AssignmentUpdate(BaseModel):
    # Optional course identifier
    course_id: Optional[str] = None
    # Optional updated title
    title: Optional[str] = None
    # Optional updated instructions
    description: Optional[str] = None
    # Optional updated deadline
    due_date: Optional[datetime] = None
    # Optional updated maximum score
    max_score: Optional[float] = None
    # Optional updated rubric ID
    rubric_id: Optional[str] = None
    # Optional updated reference solution
    reference_assignment_text: Optional[str] = None
    # Optional updated lifecycle status
    status: Optional[str] = None
    # Optional updated assignment category
    assignment_type: Optional[str] = None
    # Optional updated similarity threshold
    similarity_threshold: Optional[float] = None
    # Optional updated starter code
    starter_code: Optional[str] = None


# Schema for returning assignment data in API responses
class AssignmentResponse(VerismBaseModel):
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
    max_score: float = 100.0
    # Optional rubric identifier linked to this assignment
    rubric_id: Optional[str] = None
    # Optional exemplar or reference text for grading context
    reference_assignment_text: Optional[str] = None
    # Lifecycle status: Draft, Open, Grading, Reviewed, Published
    status: str = "Draft"
    # Assignment type
    assignment_type: str = "homework"
    # Similarity threshold percentage
    similarity_threshold: float = 70.0
    # Starter code
    starter_code: Optional[str] = None
    # Submissions count attribute and alias for UI card stats
    submissions_count: int = 0
    submission_count: int = 0
    # Count of evaluated submissions
    evaluated_count: int = 0
    # Count of graded / approved submissions
    graded_count: int = 0
    # Timestamp indicating when the assignment was created
    created_at: Optional[datetime] = None

    # Model validator synchronizing submission_count and submissions_count
    @model_validator(mode="after")
    def sync_submission_counts(self) -> "AssignmentResponse":
        """Synchronize submission_count and submissions_count so both are always present."""
        if self.submission_count == 0 and self.submissions_count > 0:
            self.submission_count = self.submissions_count
        elif self.submissions_count == 0 and self.submission_count > 0:
            self.submissions_count = self.submission_count
        return self
