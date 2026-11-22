# Module docstring explaining GradeHistory database model for immutable audit tracking of grade modifications
"""GradeHistory database model maintaining an immutable revision audit log of all grade changes."""

# Import uuid library to generate cryptographically random unique primary keys
import uuid
# Import datetime and timezone primitives for timezone-aware UTC timestamps
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, floats, JSON, text, and foreign keys
from sqlalchemy import Column, String, Float, Text, JSON, DateTime, ForeignKey
# Import ORM relationship utility for mapping related entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app core database package
from app.core.database import Base


# Database model tracking immutable revision history for student grades
class GradeHistory(Base):
    """Database model logging every score update, AI re-grade, manual override, and approval stamp.

    Preserves full reproducibility and compliance audit trails for academic reviews.
    """

    # Specify physical table name in PostgreSQL
    __tablename__ = "grade_history"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent draft grade record
    draft_grade_id = Column(String(64), ForeignKey("draft_grades.id", ondelete="CASCADE"), nullable=True, index=True)
    # Foreign key referencing target submission
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing target assignment
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    # Prompt version active during evaluation
    prompt_version_id = Column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    # Batch grading run identifier if generated during a batch execution
    grading_run_id = Column(String(36), ForeignKey("grading_runs.id", ondelete="SET NULL"), nullable=True)
    # Total score recorded in this revision
    score = Column(Float, nullable=False)
    # Maximum possible score for assignment
    max_score = Column(Float, nullable=False, default=100.0)
    # Dictionary of criterion name to numeric score
    criteria_scores = Column(JSON, nullable=True)
    # Complete criteria evaluation breakdown with justifications and citations
    criteria_breakdown = Column(JSON, nullable=True)
    # Overall qualitative feedback text
    feedback = Column(Text, nullable=True)
    # Status at time of revision (e.g. pending, approved, overridden)
    status = Column(String(32), nullable=False)
    # Nature of grade modification (initial_ai, regrade, manual_override, approved, rollback)
    change_type = Column(String(64), nullable=False)
    # User identifier who initiated the change
    changed_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Rationale or justification provided for the modification
    change_reason = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when revision was recorded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping target submission
    submission = relationship("Submission", backref="grade_history_revisions")
    # Many-to-one relationship mapping the user who authorized the change
    modifier = relationship("User", backref="grade_modifications_made")
