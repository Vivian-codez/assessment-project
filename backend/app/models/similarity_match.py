"""Similarity Match database model for peer-to-peer plagiarism detection."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class SimilarityMatch(Base):
    __tablename__ = "similarity_matches"

    id = Column(String(64), primary_key=True, index=True)
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_a_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    submission_b_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)

    similarity_score = Column(Float, nullable=False)  # e.g., 94.0
    matching_phrases = Column(JSON, default=list)  # List of exact/near matched phrases

    # Status: High similarity, Within range, Confirmed concern, Dismissed
    status = Column(String(64), default="High similarity")
    teacher_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignment = relationship("Assignment", back_populates="similarity_matches")
    submission_a = relationship("Submission", foreign_keys=[submission_a_id])
    submission_b = relationship("Submission", foreign_keys=[submission_b_id])
