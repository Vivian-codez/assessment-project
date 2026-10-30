"""Similarity Match database model for peer-to-peer plagiarism detection."""

# Import datetime class for UTC timestamp tracking
from datetime import datetime
# Import SQLAlchemy Column, column types (String, Float, DateTime, ForeignKey, Text, JSON)
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
# Import relationship construct to map links between SimilarityMatch, Assignment, and Submissions
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database
from app.core.database import Base


# Database model representing detected pairwise similarity collisions between two student submissions
class SimilarityMatch(Base):
    # Specify target physical table name in PostgreSQL
    __tablename__ = "similarity_matches"

    # Alphanumeric unique identifier for similarity match record acting as primary key
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing parent assignment in which the collision occurred (cascades on delete)
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing the first student submission in the comparison pair
    submission_a_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    # Foreign key referencing the second student submission in the comparison pair
    submission_b_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)

    # Numerical percentage score (0.0 to 100.0) indicating peer-to-peer collision severity
    similarity_score = Column(Float, nullable=False)  # e.g., 94.0
    # JSON array containing exact or near-identical matching text spans and code snippets
    matching_phrases = Column(JSON, default=list)  # List of exact/near matched phrases

    # Status: High similarity, Within range, Confirmed concern, Dismissed
    # Qualitative status tag for teacher investigation workflows
    status = Column(String(64), default="High similarity")
    # Teacher notes recording rationale, dismissal justifications, or meeting outcomes
    teacher_note = Column(Text, nullable=True)

    # UTC timestamp when the similarity match was detected and logged
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp when the match record or teacher note was last modified
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Many-to-one relationship mapping the parent assignment
    assignment = relationship("Assignment", back_populates="similarity_matches")
    # Many-to-one relationship mapping the first submission entity in the pair
    submission_a = relationship("Submission", foreign_keys=[submission_a_id])
    # Many-to-one relationship mapping the second submission entity in the pair
    submission_b = relationship("Submission", foreign_keys=[submission_b_id])
