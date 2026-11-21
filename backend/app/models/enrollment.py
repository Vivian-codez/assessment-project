# Module docstring explaining Enrollment join entity mapping students to courses
"""Enrollment database model representing student enrollment in courses and sections."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, foreign keys, and unique constraints
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing the enrollment relation between a student, course, and section
class Enrollment(Base):
    """Database model mapping student enrollments into courses and sections."""

    # Specify target physical table name in PostgreSQL
    __tablename__ = "enrollments"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing enrolled student
    student_id = Column(String(64), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing parent course
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    # Optional foreign key referencing specific section
    section_id = Column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)
    # Enrollment status string (active, dropped, auditing)
    status = Column(String(32), default="active", nullable=False)
    # Timezone-aware UTC timestamp when student was enrolled
    enrolled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Composite uniqueness constraint ensuring student is enrolled at most once per course
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    # Relationships
    # Many-to-one relationship mapping the student entity
    student = relationship("Student", backref="enrollments")
    # Many-to-one relationship mapping the course entity
    course = relationship("Course", back_populates="enrollments")
    # Many-to-one relationship mapping the section entity
    section = relationship("Section", back_populates="enrollments")

