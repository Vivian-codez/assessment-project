"""Course database model."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=False, index=True)
    section = Column(String(32), nullable=False, default="A")
    tone = Column(String(32), default="lav")  # lav, blue, sage, amber
    students_count = Column(Integer, default=0)
    instructor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instructor = relationship("Instructor", back_populates="courses")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    rubrics = relationship("Rubric", back_populates="course", cascade="all, delete-orphan")
