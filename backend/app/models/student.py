"""Student database model representing enrolled students in a classroom roster."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Student(Base):
    """Database model representing enrolled student roll call record."""
    __tablename__ = "students"

    id = Column(String(64), primary_key=True, index=True)
    classroom_id = Column(String(64), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    roll_number = Column(String(64), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("classroom_id", "roll_number", name="uq_students_classroom_roll"),
    )

    # Relationships
    classroom = relationship("Classroom", back_populates="students")
    submissions = relationship("Submission", back_populates="student")
