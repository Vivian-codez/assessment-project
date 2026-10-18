"""Instructor database model."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(128), default="Instructor · Computer Science")
    hashed_password = Column(String(255), nullable=False)
    preferences = Column(JSON, default=lambda: {
        "show_similarity_context": True,
        "require_teacher_notes_on_overrides": False,
        "include_ai_content_indicator": True,
    })
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    courses = relationship("Course", back_populates="instructor", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="actor")
