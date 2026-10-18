"""User database model for authentication."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

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


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    token = Column(String(512), index=True, nullable=False)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

