# Module docstring explaining Course Section database entity
"""Section database model representing classroom cohorts within a course."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, and foreign keys
from sqlalchemy import Column, String, DateTime, ForeignKey
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing individual sections or cohorts within a course
class Section(Base):
    """Database model representing sections/cohorts under a course.

    Allows partitioning student rosters, TA permissions, and submission
    deadlines within a single master course curriculum.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "sections"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent course
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    # Section display title or label (e.g. 'Section A', 'Morning Lab')
    name = Column(String(255), nullable=False)
    # Optional section code or catalog identifier (e.g. 'SEC-A')
    code = Column(String(64), nullable=True)
    # Timezone-aware UTC timestamp when section record was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Timezone-aware UTC timestamp when section record was last updated
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent course entity
    course = relationship("Course", back_populates="sections")
    # One-to-many relationship linking enrollments in this section
    enrollments = relationship("Enrollment", back_populates="section", cascade="all, delete-orphan")

