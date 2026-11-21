# Module docstring explaining CriterionScore database entity for normalized rubric evaluations
"""CriterionScore database model representing normalized score items within a draft grade."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, numbers, text, and foreign keys
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing a normalized individual criterion score inside a student grade
class CriterionScore(Base):
    """Database model storing granular criterion-level scores and justifications.

    Enables relational analytics, rubric reliability analysis, and student
    strength/weakness diagnostics across course cohorts.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "criterion_scores"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent draft grade
    grade_id = Column(String(64), ForeignKey("draft_grades.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing associated rubric criterion
    criterion_id = Column(String(64), ForeignKey("rubric_criteria.id", ondelete="SET NULL"), nullable=True, index=True)
    # Display name of the criterion evaluated
    criterion_name = Column(String(255), nullable=False)
    # Numerical points awarded by AI or teacher
    score = Column(Float, nullable=False, default=0.0)
    # Maximum points achievable under this criterion
    max_score = Column(Float, nullable=False, default=100.0)
    # Qualitative feedback specific to this criterion
    feedback = Column(Text, nullable=True)
    # Rationale and evidence extracted from student text justifying awarded score
    rationale = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when score was recorded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent draft grade
    draft_grade = relationship("DraftGrade", backref="criterion_score_items")
    # Many-to-one relationship mapping the rubric criterion
    criterion = relationship("RubricCriterion", backref="criterion_scores")

