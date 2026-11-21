# Module docstring explaining GradingRun database entity for batch auto-grading executions
"""GradingRun database model representing execution batches of automated grading."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, numbers, text, and foreign keys
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing a discrete batch grading execution run for an assignment
class GradingRun(Base):
    """Database model tracking batch auto-grading lifecycle runs.

    Records start, progress, completion status, and execution metrics for
    grading workflows dispatched across Celery evaluation queues.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "grading_runs"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent assignment being graded
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing user who initiated the grading run
    triggered_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Lifecycle execution status (queued, running, completed, failed)
    status = Column(String(32), default="queued", nullable=False, index=True)
    # Total count of submissions included in this grading run
    total_submissions = Column(Integer, default=0, nullable=False)
    # Count of submissions successfully evaluated so far
    completed_count = Column(Integer, default=0, nullable=False)
    # Count of submissions that failed evaluation
    failed_count = Column(Integer, default=0, nullable=False)
    # Detailed error log if execution run fails
    error_message = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when grading run was initiated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Timezone-aware UTC timestamp when grading run concluded
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # Many-to-one relationship mapping the parent assignment
    assignment = relationship("Assignment", backref="grading_runs")
    # Many-to-one relationship mapping the user who triggered the run
    operator = relationship("User", backref="grading_runs")

