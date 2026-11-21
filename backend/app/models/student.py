# Module docstring documenting the purpose of the Student roster database entity
"""Student database model representing enrolled students in a classroom roster."""

# Import datetime class for UTC timestamp tracking of student record creation
from datetime import datetime
# Import SQLAlchemy primitives for columns, data types, foreign keys, and unique table constraints
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
# Import relationship utility to define ORM navigation properties across models
from sqlalchemy.orm import relationship

# Import declarative Base class registered in application core database configuration
from app.core.database import Base


# Database ORM model representing individual enrolled student records in a classroom roster
class Student(Base):
    # Class-level docstring documenting the student database entity
    """Database model representing enrolled student roll call record."""
    # Physical table name mapping to the PostgreSQL database table
    __tablename__ = "students"

    # Primary key unique string identifier for the student roster record
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing the parent classroom section this student belongs to
    classroom_id = Column(String(64), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    # Unique academic student roll number or institutional identifier within the cohort
    roll_number = Column(String(64), nullable=False, index=True)
    # Full legal name or display name of the enrolled student
    full_name = Column(String(255), nullable=False)
    # Optional institutional or personal email address for the student
    email = Column(String(255), nullable=True)
    # UTC timestamp recording when this student entry was added to the roster
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite table constraints enforcing uniqueness per classroom
    __table_args__ = (
        # Ensure roll numbers cannot be duplicated within the same classroom cohort
        UniqueConstraint("classroom_id", "roll_number", name="uq_students_classroom_roll"),
    )

    # Relationships
    # Many-to-one relationship linking student back to parent classroom cohort
    classroom = relationship("Classroom", back_populates="students")
    # One-to-many relationship linking all assignment submissions authored by this student
    submissions = relationship("Submission", back_populates="student")
