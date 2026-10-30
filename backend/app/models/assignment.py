"""Assignment database model."""

# Import datetime class for recording creation and update timestamps
from datetime import datetime
# Import SQLAlchemy Column, data types, and ForeignKey constraint specification
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
# Import relationship construct to map connections between Assignment, Course, Rubric, and Submissions
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database
from app.core.database import Base


# Database model representing academic assignments and homework assessments
class Assignment(Base):
    # Specify target physical table name in PostgreSQL
    __tablename__ = "assignments"

    # Alphanumeric unique identifier for assignment acting as primary key
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing the parent course (cascades deletions when course is removed)
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    # Title or headline of the assignment (e.g. 'Assignment 3 · Graph Traversal')
    title = Column(String(255), nullable=False)  # e.g. "Assignment 3 · Graph Traversal"
    # Detailed instructions, requirements, and prompt text provided to students
    description = Column(Text, nullable=True)
    # Submission deadline timestamp
    due_date = Column(DateTime, nullable=True)
    # Maximum achievable point score for this assignment (defaults to 100.0)
    max_score = Column(Float, default=100.0)
    # Foreign key referencing the evaluation rubric used for grading (set to NULL if rubric deleted)
    rubric_id = Column(String(64), ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True)
    # Teacher reference exemplar solution text used by AI for grounding and benchmarking
    reference_assignment_text = Column(Text, nullable=True)  # Exemplar solution/ground truth
    # UTC timestamp recording when the assignment was configured
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp recording when assignment attributes were last modified
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Many-to-one relationship mapping the parent course entity
    course = relationship("Course", back_populates="assignments")
    # Many-to-one relationship mapping the associated evaluation rubric
    rubric = relationship("Rubric", back_populates="assignments")
    # One-to-many relationship mapping student submissions submitted for this assignment (cascades on delete)
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")
    # One-to-many relationship mapping pairwise similarity collision records for this assignment
    similarity_matches = relationship("SimilarityMatch", back_populates="assignment", cascade="all, delete-orphan")
