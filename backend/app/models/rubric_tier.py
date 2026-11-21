# Module docstring explaining RubricTier database entity for granular performance levels
"""RubricTier database model representing discrete scoring tiers within a rubric criterion."""

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


# Database model representing discrete performance tiers or achievement levels inside a rubric criterion
class RubricTier(Base):
    """Database model representing discrete performance levels within a criterion.

    Maps performance standards such as Exemplary (4 pts), Proficient (3 pts),
    Developing (2 pts), and Novice (1 pt) with explicit descriptions.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "rubric_tiers"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent rubric criterion
    criterion_id = Column(String(64), ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False, index=True)
    # Tier level title (e.g. 'Exemplary', 'Proficient')
    name = Column(String(255), nullable=False)
    # Numerical points awarded for this tier
    points = Column(Float, nullable=False, default=0.0)
    # Detailed textual guidelines explaining what constitutes performance at this tier
    description = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when tier was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent criterion
    criterion = relationship("RubricCriterion", backref="tiers")

