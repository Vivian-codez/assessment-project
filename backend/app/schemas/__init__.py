"""Pydantic v2 Validation Schemas Package."""

from app.schemas.auth import Token, TokenPayload, InstructorLogin, InstructorResponse, TeacherPreferencesUpdate
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse
from app.schemas.rubric import RubricCriterionSchema, RubricCreate, RubricResponse
from app.schemas.assignment import AssignmentCreate, AssignmentResponse
from app.schemas.submission import SubmissionCreate, SubmissionResponse, SubmissionDetailResponse, BatchUploadResponse
from app.schemas.grading import CriterionScoreSchema, GradeApprovalRequest, FlagActionRequest, DraftGradeResponse, StructuredGradingOutput
from app.schemas.similarity import SimilarityPairResponse, SimilarityCheckOverviewResponse
from app.schemas.job import BatchEvaluationRequest, BatchJobResponse
from app.schemas.gradebook import GradebookEntryResponse, GradebookResponse
from app.schemas.report import ReportResponse

__all__ = [
    "Token",
    "TokenPayload",
    "InstructorLogin",
    "InstructorResponse",
    "TeacherPreferencesUpdate",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "RubricCriterionSchema",
    "RubricCreate",
    "RubricResponse",
    "AssignmentCreate",
    "AssignmentResponse",
    "SubmissionCreate",
    "SubmissionResponse",
    "SubmissionDetailResponse",
    "BatchUploadResponse",
    "CriterionScoreSchema",
    "GradeApprovalRequest",
    "FlagActionRequest",
    "DraftGradeResponse",
    "StructuredGradingOutput",
    "SimilarityPairResponse",
    "SimilarityCheckOverviewResponse",
    "BatchEvaluationRequest",
    "BatchJobResponse",
    "GradebookEntryResponse",
    "GradebookResponse",
    "ReportResponse",
]
