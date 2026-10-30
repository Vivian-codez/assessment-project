"""Rubric and Rubric Criteria database models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Rubric(Base):
    """Database model representing assessment rubrics containing scoring matrices."""
    __tablename__ = "rubrics"

    id = Column(String(64), primary_key=True, index=True)
    classroom_id = Column(String(64), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    total_marks = Column(Float, default=0.0)
    total_max_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    classroom = relationship("Classroom", back_populates="rubrics")
    course = relationship("Course", back_populates="rubrics")
    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan", order_by="RubricCriterion.order_index")
    assignments = relationship("Assignment", back_populates="rubric")


class RubricCriterion(Base):
    """Database model representing individual scoring criteria within an evaluation rubric."""
    __tablename__ = "rubric_criteria"

    id = Column(String(64), primary_key=True, index=True)
    rubric_id = Column(String(64), ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False, index=True)
    criterion_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    weight = Column(Float, nullable=False, default=25.0)
    max_points = Column(Float, nullable=False, default=4.0)
    max_score = Column(Float, nullable=False, default=4.0)
    order_index = Column(Integer, default=0)
    levels = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rubric = relationship("Rubric", back_populates="criteria")
