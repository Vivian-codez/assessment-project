"""Database Models Package."""

# Import declarative Base class from app.core.database to expose for schema binding
from app.core.database import Base
# Import User authentication entity and UserSession token tracking model from app.models.user
from app.models.user import User, UserSession
# Import Instructor profile and credentials model from app.models.instructor
from app.models.instructor import Instructor
# Import Course curriculum and classroom mapping model from app.models.course
from app.models.course import Course
# Import Classroom and Student roster models
from app.models.classroom import Classroom
from app.models.student import Student
# Import Rubric matrix container and RubricCriterion evaluation category models from app.models.rubric
from app.models.rubric import Rubric, RubricCriterion
# Import Assignment task definition and prompt exemplar model from app.models.assignment
from app.models.assignment import Assignment
# Import Submission student document and evaluation state model from app.models.submission
from app.models.submission import Submission
# Import DraftGrade AI evaluation recommendation and teacher approval model from app.models.draft_grade
from app.models.draft_grade import DraftGrade
# Import SimilarityMatch peer collision pair and shared phrase model from app.models.similarity_match
from app.models.similarity_match import SimilarityMatch
# Import BatchJob background Celery processing tracking model from app.models.batch_job
from app.models.batch_job import BatchJob
# Import AuditLog immutable compliance and security audit trail model from app.models.audit_log
from app.models.audit_log import AuditLog

# Export public model symbols for easy package-level importing across backend services
__all__ = [
    # Declarative base class
    "Base",
    # Local user account model
    "User",
    # Active JWT user session model
    "UserSession",
    # Educator profile model
    "Instructor",
    # Academic course model
    "Course",
    # Classroom model
    "Classroom",
    # Student roster model
    "Student",
    # Evaluation rubric container model
    "Rubric",
    # Detailed rubric criterion model
    "RubricCriterion",
    # Student assignment model
    "Assignment",
    # Student work submission model
    "Submission",
    # Teacher draft grade model
    "DraftGrade",
    # Peer similarity collision match model
    "SimilarityMatch",
    # Background batch job model
    "BatchJob",
    # FERPA/GDPR audit log model
    "AuditLog",
]
