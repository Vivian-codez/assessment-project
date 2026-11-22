# Module docstring explaining DryRun and DryRunResult database models for isolated evaluation testing
"""DryRun and DryRunResult database models for sandbox testing of candidate prompt versions."""

# Import uuid library to generate cryptographically random unique primary keys
import uuid
# Import datetime and timezone primitives for timezone-aware UTC timestamps
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, booleans, floats, JSON, text, and foreign keys
from sqlalchemy import Column, String, Float, Text, Boolean, JSON, DateTime, ForeignKey
# Import ORM relationship utility for mapping related entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app core database package
from app.core.database import Base


# Database model tracking isolated non-destructive dry-run simulation sessions
class DryRun(Base):
    """Database model tracking isolated sandbox testing of candidate prompt improvements.

    Evaluates a representative sample of student submissions with draft instructions
    without overwriting production grades in the live gradebook.
    """

    # Specify physical table name in PostgreSQL
    __tablename__ = "dry_runs"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Baseline prompt version being benchmarked against
    prompt_version_id = Column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    # Foreign key referencing target assignment
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    # List of submission identifiers included in this test sample cohort
    sample_submission_ids = Column(JSON, nullable=False)
    # Proposed candidate extra instructions being tested
    draft_extra_instructions = Column(Text, nullable=True)
    # Proposed candidate few-shot examples serialized as JSON
    draft_few_shot_examples = Column(JSON, nullable=True)
    # Execution lifecycle status (pending, running, completed, failed)
    status = Column(String(32), default="pending", nullable=False)
    # Aggregate summary metrics (agreement_rate, score_delta, regressions_count)
    summary_metrics = Column(JSON, nullable=True)
    # User identifier of the teacher who dispatched the dry run
    created_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Timezone-aware UTC timestamp when dry run was initiated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Timezone-aware UTC timestamp when dry run completed
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # Many-to-one relationship mapping the baseline prompt version
    prompt_version = relationship("PromptVersion", backref="dry_runs")
    # Many-to-one relationship mapping target assignment
    assignment = relationship("Assignment", backref="dry_runs")
    # Many-to-one relationship mapping the authoring teacher user
    author = relationship("User", backref="dry_runs")
    # One-to-many relationship mapping individual criteria comparison results
    results = relationship("DryRunResult", back_populates="dry_run", cascade="all, delete-orphan")


# Database model storing criterion-level before/after comparison results for a dry run
class DryRunResult(Base):
    """Database model recording before/after criteria scores, tier diffs, and regression flags."""

    # Specify physical table name in PostgreSQL
    __tablename__ = "dry_run_results"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent dry run session
    dry_run_id = Column(String(36), ForeignKey("dry_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing submission evaluated
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    # Rubric criterion evaluated
    criterion_id = Column(String(64), nullable=True)
    # Previous rubric tier assigned under baseline prompt
    old_tier_id = Column(String(64), nullable=True)
    # Newly suggested rubric tier under draft prompt
    new_tier_id = Column(String(64), nullable=True)
    # Teacher corrected tier target (ground truth)
    teacher_corrected_tier_id = Column(String(64), nullable=True)
    # Previous numeric score points
    old_points = Column(Float, nullable=True)
    # Newly calculated numeric score points
    new_points = Column(Float, nullable=True)
    # Teacher benchmark target score points
    teacher_points = Column(Float, nullable=True)
    # Flag indicating whether this change was a regression moving further from teacher target
    is_regression = Column(Boolean, default=False, nullable=False)
    # Previous qualitative justification text
    old_justification = Column(Text, nullable=True)
    # Newly generated qualitative justification text
    new_justification = Column(Text, nullable=True)
    # Previous citation snippets serialized as JSON
    old_evidence = Column(JSON, nullable=True)
    # Newly cited citation snippets serialized as JSON
    new_evidence = Column(JSON, nullable=True)
    # Creation timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping parent dry run
    dry_run = relationship("DryRun", back_populates="results")
    # Many-to-one relationship mapping target submission
    submission = relationship("Submission", backref="dry_run_results")
