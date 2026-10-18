"""Draft Grade database model."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class DraftGrade(Base):
    __tablename__ = "draft_grades"

    id = Column(String(64), primary_key=True, index=True)
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False)

    suggested_score = Column(Float, nullable=False, default=0.0)
    final_score = Column(Float, nullable=True)  # Populated only upon Teacher Approval

    # Structured rubric breakdown:
    # [{"criterion_name": "Understanding", "score": 25, "max": 30, "rationale": "..."}]
    criteria_scores = Column(JSON, nullable=False, default=list)

    ai_feedback = Column(Text, nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    # Status: pending, flagged, approved
    status = Column(String(32), default="pending", index=True)

    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True)
    ai_model = Column(String(64), default="gemini-2.5-flash")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    submission = relationship("Submission", back_populates="draft_grade")
    approved_by = relationship("Instructor")
