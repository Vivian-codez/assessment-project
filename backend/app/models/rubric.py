"""Rubric and Rubric Criteria database models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    total_max_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="rubrics")
    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan", order_by="RubricCriterion.order_index")
    assignments = relationship("Assignment", back_populates="rubric")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(String(64), primary_key=True, index=True)
    rubric_id = Column(String(64), ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Understanding", "Accuracy", "Methodology"
    description = Column(Text, nullable=True)   # e.g., "Conceptual clarity and depth"
    weight = Column(Float, nullable=False, default=25.0)  # percentage weight (e.g. 30%)
    max_score = Column(Float, nullable=False, default=30.0)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rubric = relationship("Rubric", back_populates="criteria")
