# Module docstring explaining PromptVersion database model for versioned AI grading instructions
"""PromptVersion database model supporting teacher customization and version control of LLM grading prompts."""

# Import uuid library to generate cryptographically random unique primary keys
import uuid
# Import datetime and timezone primitives for timezone-aware UTC timestamps
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, booleans, integers, JSON, and foreign keys
from sqlalchemy import Column, String, Integer, Text, Boolean, JSON, DateTime, ForeignKey
# Import ORM relationship utility for mapping related entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app core database package
from app.core.database import Base


# Database model tracking versioned LLM prompt configurations for rubric grading
class PromptVersion(Base):
    """Database model storing version-controlled AI grading prompts and safety guidelines.

    Allows educators to maintain an immutable locked base instruction layer while
    iterating on domain-specific guidelines, few-shot calibration examples, and scoring tolerances.
    """

    # Specify table name in PostgreSQL
    __tablename__ = "prompt_versions"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent assignment (nullable for global educator default templates)
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True, index=True)
    # Monotonically increasing version number for the target assignment
    version_number = Column(Integer, nullable=False, default=1)
    # Functional classification of prompt (e.g. 'grading', 'plagiarism_explanation')
    prompt_type = Column(String(64), default="grading", nullable=False)
    # Immutable system prompt base instructions enforcing core grading rules and schemas
    locked_base_instructions = Column(Text, nullable=False)
    # Editable guidelines customized by the teacher for this assignment
    extra_teacher_instructions = Column(Text, nullable=True)
    # Calibrated few-shot grading examples serialized as JSON list
    few_shot_examples = Column(JSON, nullable=True)
    # Similarity and AI detection score thresholds serialized as JSON object
    thresholds = Column(JSON, nullable=True)
    # Changelog entry or release notes for this prompt revision
    note = Column(String(255), nullable=True)
    # User identifier of the teacher who authored or approved this version
    created_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Flag indicating whether this is the currently active version for auto-grading
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    # Timezone-aware UTC timestamp when prompt version was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the target assignment
    assignment = relationship("Assignment", backref="prompt_versions")
    # Many-to-one relationship mapping the authoring educator user
    author = relationship("User", backref="created_prompts")
