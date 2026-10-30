# Module docstring explaining that this package aggregates all Pydantic v2 validation schemas
"""Pydantic v2 Validation Schemas Package."""

# Import authentication and token data models from the auth schema module
from app.schemas.auth import Token, TokenPayload, InstructorLogin, InstructorResponse, TeacherPreferencesUpdate
# Import course creation, update, and response data models from the course schema module
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse
# Import rubric criterion, creation, and response data models from the rubric schema module
from app.schemas.rubric import RubricCriterionSchema, RubricCreate, RubricResponse
# Import assignment creation and response models from the assignment schema module
from app.schemas.assignment import AssignmentCreate, AssignmentResponse
# Import submission handling and batch upload models from the submission schema module
from app.schemas.submission import SubmissionCreate, SubmissionResponse, SubmissionDetailResponse, BatchUploadResponse
# Import grading review, score breakdown, and approval models from the grading schema module
from app.schemas.grading import CriterionScoreSchema, GradeApprovalRequest, FlagActionRequest, DraftGradeResponse, StructuredGradingOutput
# Import plagiarism and text similarity models from the similarity schema module
from app.schemas.similarity import SimilarityPairResponse, SimilarityCheckOverviewResponse
# Import background batch evaluation job models from the job schema module
from app.schemas.job import BatchEvaluationRequest, BatchJobResponse
# Import gradebook entry and overall gradebook response models from the gradebook schema module
from app.schemas.gradebook import GradebookEntryResponse, GradebookResponse
# Import analytics and export report models from the report schema module
from app.schemas.report import ReportResponse

# Define the explicit list of symbols exported when importing from the schemas package
__all__ = [
    # Export authentication token model
    "Token",
    # Export JWT token payload model
    "TokenPayload",
    # Export instructor login credentials model
    "InstructorLogin",
    # Export instructor response profile model
    "InstructorResponse",
    # Export teacher preferences update schema
    "TeacherPreferencesUpdate",
    # Export course creation request schema
    "CourseCreate",
    # Export course update request schema
    "CourseUpdate",
    # Export course summary response schema
    "CourseResponse",
    # Export detailed course response schema
    "CourseDetailResponse",
    # Export rubric individual criterion schema
    "RubricCriterionSchema",
    # Export rubric creation request schema
    "RubricCreate",
    # Export rubric response schema
    "RubricResponse",
    # Export assignment creation request schema
    "AssignmentCreate",
    # Export assignment response schema
    "AssignmentResponse",
    # Export submission creation request schema
    "SubmissionCreate",
    # Export submission summary response schema
    "SubmissionResponse",
    # Export detailed submission response schema
    "SubmissionDetailResponse",
    # Export bulk ZIP upload response schema
    "BatchUploadResponse",
    # Export criterion score breakdown schema
    "CriterionScoreSchema",
    # Export instructor grade approval request schema
    "GradeApprovalRequest",
    # Export submission flag update request schema
    "FlagActionRequest",
    # Export AI draft grade response schema
    "DraftGradeResponse",
    # Export structured LLM grading output schema
    "StructuredGradingOutput",
    # Export pairwise similarity match response schema
    "SimilarityPairResponse",
    # Export overall similarity check summary schema
    "SimilarityCheckOverviewResponse",
    # Export batch evaluation background request schema
    "BatchEvaluationRequest",
    # Export batch job status response schema
    "BatchJobResponse",
    # Export individual gradebook student entry schema
    "GradebookEntryResponse",
    # Export full course gradebook response schema
    "GradebookResponse",
    # Export summary report response schema
    "ReportResponse",
]
