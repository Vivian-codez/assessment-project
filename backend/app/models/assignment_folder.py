"""AssignmentFolder, FolderSubmission, EvaluationResult, and MonthlyUsage SQLAlchemy models.

Implements multi-tenant, user-scoped schema for AI assignment evaluation pipeline.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssignmentFolder(Base):
    """AssignmentFolder represents a collection of student submissions scoped to a user/tenant."""

    __tablename__ = "assignment_folders"

    # Alphanumeric UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Multi-tenant user scope foreign key
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Folder title / assignment label
    title = Column(String(255), nullable=False)

    # Specific rubric text used for evaluating submissions in this folder
    rubric_text = Column(Text, nullable=False)

    # Folder evaluation processing state: 'pending', 'processing', 'completed'
    status = Column(String(32), default="pending", nullable=False, index=True)

    # Creation timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="assignment_folders")
    submissions = relationship(
        "FolderSubmission",
        back_populates="folder",
        cascade="all, delete-orphan",
        order_by="FolderSubmission.created_at",
    )


class FolderSubmission(Base):
    """FolderSubmission represents an individual student submission within an AssignmentFolder."""

    __tablename__ = "folder_submissions"

    # UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Foreign key referencing parent AssignmentFolder
    folder_id = Column(
        String(36),
        ForeignKey("assignment_folders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Student identifier (e.g. roll number, email, or student ID)
    student_identifier = Column(String(255), nullable=True, index=True)

    # Storage path to submission file on disk
    file_path = Column(String(512), nullable=True)

    # Extracted or parsed text content
    extracted_text = Column(Text, nullable=True)

    # Evaluation processing status: 'unprocessed', 'processing', 'completed', 'deferred', 'quota_deferred'
    evaluation_status = Column(String(32), default="unprocessed", nullable=False, index=True)

    # Creation timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    folder = relationship("AssignmentFolder", back_populates="submissions")
    evaluation_result = relationship(
        "EvaluationResult",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )


# Alias Submission to FolderSubmission for API compatibility
Submission = FolderSubmission


class EvaluationResult(Base):
    """EvaluationResult stores structured grading outputs from Gemini per submission."""

    __tablename__ = "evaluation_results"

    # UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Foreign key referencing parent submission (one-to-one, unique)
    submission_id = Column(
        String(36),
        ForeignKey("folder_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Numeric evaluation score (e.g. 0.0 to 100.0)
    score = Column(Float, nullable=False)

    # Structured feedback and criteria breakdown JSON document
    feedback_json = Column(JSON, nullable=False)

    # Timestamp when evaluation was conducted
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship back to submission
    submission = relationship("FolderSubmission", back_populates="evaluation_result")


class MonthlyUsage(Base):
    """MonthlyUsage tracks user quota and token consumption per billing month."""

    __tablename__ = "monthly_usages"
    __table_args__ = (
        UniqueConstraint("user_id", "billing_month", name="uq_user_billing_month"),
    )

    # UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # Tenant user identifier
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Billing month in YYYY-MM format (e.g. "2026-11")
    billing_month = Column(String(7), nullable=False, index=True)

    # Count of submissions evaluated in this billing cycle
    submissions_evaluated = Column(Integer, default=0, nullable=False)

    # Total Gemini API tokens consumed during this billing cycle
    token_count = Column(BigInteger, default=0, nullable=False)

    # Timestamp records
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to User
    user = relationship("User", back_populates="monthly_usages")
