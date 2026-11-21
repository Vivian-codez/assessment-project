# Module docstring explaining the purpose of the Classroom database entity
"""Classroom database model representing instructional sections and cohorts."""

# Import datetime class for UTC timestamp tracking of record creation and updates
from datetime import datetime
# Import SQLAlchemy primitives for defining database columns and foreign key relations
from sqlalchemy import Column, String, DateTime, ForeignKey
# Import relationship utility to define ORM navigation properties across models
from sqlalchemy.orm import relationship

# Import declarative Base class registered in application core database configuration
from app.core.database import Base


# Database ORM model representing instructional classroom sections for enrolled students
class Classroom(Base):
    # Class-level docstring documenting the database entity functionality
    """Database model representing classrooms/sections for student enrollment."""
    # Physical table name mapping to the PostgreSQL database table
    __tablename__ = "classrooms"

    # Primary key unique string identifier for the classroom record
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key link referencing the instructor record who manages this classroom
    instructor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True, index=True)
    # Full display title or section name for the classroom cohort
    name = Column(String(255), nullable=False)
    # Short alphanumeric course code or catalog reference for the cohort
    code = Column(String(64), nullable=False, index=True)
    # UTC timestamp representing when the classroom was initially created
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp automatically refreshed whenever classroom attributes are modified
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Navigation property referencing the assigned instructor managing this classroom
    instructor = relationship("Instructor", backref="classrooms")
    # One-to-many relationship linking all enrolled students in this classroom roster
    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    # One-to-many relationship linking custom scoring rubrics configured for this classroom
    rubrics = relationship("Rubric", back_populates="classroom", cascade="all, delete-orphan")
    # One-to-many relationship linking student assignment submissions submitted in this classroom
    submissions = relationship("Submission", back_populates="classroom")
