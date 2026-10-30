"""Classroom database model representing instructional sections and cohorts."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Classroom(Base):
    """Database model representing classrooms/sections for student enrollment."""
    __tablename__ = "classrooms"

    id = Column(String(64), primary_key=True, index=True)
    instructor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instructor = relationship("Instructor", backref="classrooms")
    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    rubrics = relationship("Rubric", back_populates="classroom", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="classroom")
