# Module docstring explaining PromptFeedback database model for teacher error logging
"""PromptFeedback database model tracking teacher corrections on AI grading criteria."""

# Import uuid library to generate cryptographically random unique primary keys
import uuid
# Import datetime and timezone primitives for timezone-aware UTC timestamps
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, booleans, floats, text, and foreign keys
from sqlalchemy import Column, String, Float, Text, Boolean, DateTime, ForeignKey
# Import ORM relationship utility for mapping related entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app core database package
from app.core.database import Base


# Database model tracking educator corrections and reason classifications on AI grading
class PromptFeedback(Base):
    """Database model logging teacher disagreements and error classifications.

    Feeds into the Meta-Prompt Assistant to analyze systematic errors and propose
    prompt diffs to resolve criteria misunderstandings.
    """

    # Specify physical table name in PostgreSQL
    __tablename__ = "prompt_feedback"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing the prompt version active during evaluation
    prompt_version_id = Column(String(36), ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    # Foreign key referencing evaluated submission
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing target assignment
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    # Target rubric criterion identifier
    criterion_id = Column(String(64), nullable=True)
    # AI-assigned rubric tier identifier
    ai_tier_id = Column(String(64), nullable=True)
    # Teacher-corrected rubric tier identifier
    teacher_tier_id = Column(String(64), nullable=True)
    # AI suggested numeric criterion score
    ai_score = Column(Float, nullable=True)
    # Teacher corrected numeric criterion score
    teacher_score = Column(Float, nullable=True)
    # Reason classification (too_harsh, too_lenient, missed_evidence, misread_rubric, etc.)
    reason = Column(String(128), nullable=False)
    # Qualitative educator notes and critique
    teacher_notes = Column(Text, nullable=True)
    # User identifier of the teacher who logged the feedback
    created_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Flag indicating whether this feedback item has been addressed in a subsequent prompt version
    resolved = Column(Boolean, default=False, nullable=False)
    # Timezone-aware UTC timestamp when feedback was recorded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the active prompt version
    prompt_version = relationship("PromptVersion", backref="feedback_items")
    # Many-to-one relationship mapping the target submission
    submission = relationship("Submission", backref="prompt_feedback_records")
    # Many-to-one relationship mapping the authoring teacher user
    author = relationship("User", backref="prompt_feedback_submitted")
