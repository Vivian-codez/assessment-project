"""Assignment database model."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String(64), primary_key=True, index=True)
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)  # e.g. "Assignment 3 · Graph Traversal"
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    max_score = Column(Float, default=100.0)
    rubric_id = Column(String(64), ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True)
    reference_assignment_text = Column(Text, nullable=True)  # Exemplar solution/ground truth
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="assignments")
    rubric = relationship("Rubric", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")
    similarity_matches = relationship("SimilarityMatch", back_populates="assignment", cascade="all, delete-orphan")
