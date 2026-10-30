"""Instructor database model."""

# Import datetime class for UTC timestamp tracking
from datetime import datetime
# Import SQLAlchemy Column and SQL column data type representations
from sqlalchemy import Column, String, DateTime, Text, JSON
# Import relationship construct to establish ORM entity associations
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database
from app.core.database import Base


# Database model representing educators and faculty members managing classrooms and evaluations
class Instructor(Base):
    # Specify target physical table name in PostgreSQL
    __tablename__ = "instructors"

    # Alphanumeric unique identifier for instructor acting as primary key
    id = Column(String(64), primary_key=True, index=True)
    # Full display or legal name of the instructor
    name = Column(String(255), nullable=False)
    # Unique email address utilized for login authentication and correspondence
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Academic department role or faculty designation
    role = Column(String(128), default="Instructor · Computer Science")
    # Bcrypt-hashed password string for authentication verification
    hashed_password = Column(String(255), nullable=False)
    # JSON dictionary storing instructor preferences for UI cards and evaluation thresholds
    preferences = Column(JSON, default=lambda: {
        # Enable context snippet display beside similarity match percentages
        "show_similarity_context": True,
        # Require teacher notes when manually overriding AI evaluation scores
        "require_teacher_notes_on_overrides": False,
        # Display the AI content indicator indicator in submission review queues
        "include_ai_content_indicator": True,
    })
    # UTC timestamp when the instructor account was first registered
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp when the instructor profile was last updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # One-to-many relationship mapping courses owned by this instructor (cascades on delete)
    courses = relationship("Course", back_populates="instructor", cascade="all, delete-orphan")
    # One-to-many relationship mapping audit logs initiated by this instructor
    audit_logs = relationship("AuditLog", back_populates="actor")
