# Module docstring explaining the evaluation rubric and scoring criteria models
"""Rubric and Rubric Criteria database models."""

# Import datetime class for UTC timestamp tracking of rubric creation and updates
from datetime import datetime
# Import SQLAlchemy primitives for defining database columns, data types, constraints, and JSON fields
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
# Import relationship utility to define ORM navigation properties across models
from sqlalchemy.orm import relationship

# Import declarative Base class registered in application core database configuration
from app.core.database import Base


# Database ORM model representing evaluation rubrics containing scoring criteria matrices
class Rubric(Base):
    # Class-level docstring documenting the rubric database entity
    """Database model representing assessment rubrics containing scoring matrices."""
    # Physical table name mapping to the PostgreSQL database table
    __tablename__ = "rubrics"

    # Primary key unique string identifier for the rubric record
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key link referencing optional specific classroom section using this rubric
    classroom_id = Column(String(64), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=True, index=True)
    # Foreign key link referencing parent course curriculum associated with this rubric
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    # Optional descriptive title of the rubric (e.g. 'Data Structures Milestone 1 Rubric')
    title = Column(String(255), nullable=True)
    # Standard name string for the rubric displayed in assignment configurations
    name = Column(String(255), nullable=True)
    # Total marks allocated across all criteria in this rubric
    total_marks = Column(Float, default=0.0)
    # Maximum achievable cumulative score for assignments graded with this rubric
    total_max_score = Column(Float, default=100.0)
    # UTC timestamp representing when the rubric was initially created
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp automatically updated whenever rubric settings are modified
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Many-to-one relationship mapping the classroom section assigned to this rubric
    classroom = relationship("Classroom", back_populates="rubrics")
    # Many-to-one relationship mapping the overarching course this rubric belongs to
    course = relationship("Course", back_populates="rubrics")
    # One-to-many relationship linking individual criteria rows ordered by index
    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan", order_by="RubricCriterion.order_index")
    # One-to-many relationship linking assignments that utilize this rubric for grading
    assignments = relationship("Assignment", back_populates="rubric")


# Database ORM model representing individual scoring criteria rows inside a parent rubric
class RubricCriterion(Base):
    # Class-level docstring documenting the criterion database entity
    """Database model representing individual scoring criteria within an evaluation rubric."""
    # Physical table name mapping to the PostgreSQL database table
    __tablename__ = "rubric_criteria"

    # Primary key unique string identifier for the criterion row
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing parent rubric containing this criterion
    rubric_id = Column(String(64), ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False, index=True)
    # Optional specific name of the criterion category (e.g. 'Algorithmic Correctness')
    criterion_name = Column(String(255), nullable=True)
    # Display name for the criterion evaluated during grading
    name = Column(String(255), nullable=True)
    # Detailed textual guidelines describing what expectations must be met for this criterion
    description = Column(Text, nullable=True)
    # Percentage weight or proportion this criterion contributes to the overall grade
    weight = Column(Float, nullable=False, default=25.0)
    # Maximum point value achievable under this specific criterion
    max_points = Column(Float, nullable=False, default=4.0)
    # Maximum numeric score attainable for this criterion
    max_score = Column(Float, nullable=False, default=4.0)
    # Sorting sequence order determining display placement in the rubric table
    order_index = Column(Integer, default=0)
    # JSON array containing structured descriptive levels (e.g. Exemplary, Proficient, Developing)
    levels = Column(JSON, default=list)
    # UTC timestamp recording when this criterion entry was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    # Many-to-one relationship linking criterion back to its parent rubric
    rubric = relationship("Rubric", back_populates="criteria")
