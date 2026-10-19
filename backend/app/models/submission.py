"""Submission database model with FERPA/GDPR encryption handlers."""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import ferpa_cipher


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String(64), primary_key=True, index=True)
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)

    # FERPA/GDPR Encrypted Student Information
    student_name_encrypted = Column(Text, nullable=False)
    student_roll_encrypted = Column(Text, nullable=False)
    student_email_encrypted = Column(Text, nullable=True)

    # File and Submission Metadata
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=True)
    file_type = Column(String(64), default="pdf")
    extracted_text = Column(Text, nullable=True)
    file_content = Column(Text, nullable=True)  # Raw file content (text or base64) stored directly in database

    # Plagiarism / Similarity & AI Indicators
    similarity_score = Column(Float, default=0.0)  # Highest similarity % found with any peer
    ai_content_probability = Column(Float, default=0.0)  # 0 to 100%
    web_plagiarism_score = Column(Float, default=0.0)  # 0 to 100% public web plagiarism
    web_sources = Column(JSON, default=list)  # [{'url': ..., 'title': ..., 'match_pct': ...}]

    # Status: pending, processing, flagged, graded, approved
    status = Column(String(32), default="pending", index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    draft_grade = relationship("DraftGrade", back_populates="submission", uselist=False, cascade="all, delete-orphan")

    # Transparent FERPA Decrypt/Encrypt Property Accessors
    @property
    def student_name(self) -> str:
        return ferpa_cipher.decrypt(self.student_name_encrypted) or ""

    @student_name.setter
    def student_name(self, value: str):
        self.student_name_encrypted = ferpa_cipher.encrypt(value)

    @property
    def student_roll(self) -> str:
        return ferpa_cipher.decrypt(self.student_roll_encrypted) or ""

    @student_roll.setter
    def student_roll(self, value: str):
        self.student_roll_encrypted = ferpa_cipher.encrypt(value)

    @property
    def student_email(self) -> str:
        return ferpa_cipher.decrypt(self.student_email_encrypted) or ""

    @student_email.setter
    def student_email(self, value: str):
        self.student_email_encrypted = ferpa_cipher.encrypt(value)
