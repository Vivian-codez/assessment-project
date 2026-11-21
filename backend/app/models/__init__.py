# Module docstring explaining package-level database models and exports
"""Database Models Package."""

# Import declarative Base class from app.core.database to expose for schema binding
from app.core.database import Base
# Import Organization institutional model
from app.models.organization import Organization
# Import User authentication entity and UserSession token tracking model
from app.models.user import User, UserSession
# Import RefreshToken model for rotating sessions
from app.models.refresh_token import RefreshToken
# Import Instructor profile and credentials model
from app.models.instructor import Instructor
# Import Course curriculum and Section models
from app.models.course import Course
from app.models.section import Section
# Import Classroom, Student, and Enrollment roster models
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.enrollment import Enrollment
# Import Rubric matrix container, RubricCriterion, and RubricTier models
from app.models.rubric import Rubric, RubricCriterion
from app.models.rubric_tier import RubricTier
# Import Assignment task definition and ReferenceFile exemplar model
from app.models.assignment import Assignment
from app.models.reference_file import ReferenceFile
# Import multi-tenant evaluation folder, result, and usage models
from app.models.assignment_folder import AssignmentFolder, FolderSubmission, EvaluationResult, MonthlyUsage
# Import Submission and SubmissionFile models
from app.models.submission import Submission
from app.models.submission_file import SubmissionFile
# Import GradingRun execution tracking model
from app.models.grading_run import GradingRun
# Import DraftGrade and CriterionScore models
from app.models.draft_grade import DraftGrade
from app.models.criterion_score import CriterionScore
# Import SimilarityMatch peer collision pair model
from app.models.similarity_match import SimilarityMatch
# Import IntegrityFlag academic concern tracking model
from app.models.integrity_flag import IntegrityFlag
# Import Export gradebook archive model
from app.models.export import Export
# Import DeletionRequest right-to-be-forgotten compliance model
from app.models.deletion_request import DeletionRequest
# Import BatchJob background Celery processing tracking model
from app.models.batch_job import BatchJob
# Import AuditLog immutable compliance and security audit trail model
from app.models.audit_log import AuditLog

# Export public model symbols for easy package-level importing across backend services
__all__ = [
    # Declarative base class
    "Base",
    # Institutional tenant model
    "Organization",
    # Local user account model
    "User",
    # Active JWT user session model
    "UserSession",
    # Rotating refresh token model
    "RefreshToken",
    # Educator profile model
    "Instructor",
    # Academic course and section models
    "Course",
    "Section",
    # Classroom and student models
    "Classroom",
    "Student",
    "Enrollment",
    # Evaluation rubric models
    "Rubric",
    "RubricCriterion",
    "RubricTier",
    # Assignment and reference exemplar models
    "Assignment",
    "ReferenceFile",
    # Multi-tenant evaluation pipeline models
    "AssignmentFolder",
    "FolderSubmission",
    "EvaluationResult",
    "MonthlyUsage",
    # Submission models
    "Submission",
    "SubmissionFile",
    # Batch grading execution runs
    "GradingRun",
    # Grade and criterion score breakdown models
    "DraftGrade",
    "CriterionScore",
    # Similarity detection models
    "SimilarityMatch",
    # Academic honesty flag model
    "IntegrityFlag",
    # Gradebook export model
    "Export",
    # Right-to-be-forgotten deletion request model
    "DeletionRequest",
    # Celery batch background job model
    "BatchJob",
    # FERPA security audit log model
    "AuditLog",
]
