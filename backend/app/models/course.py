# Module docstring explaining Course database entity
"""Course database model."""

# Import datetime class for UTC timestamp tracking
from datetime import datetime
# Import Column and SQL data types along with ForeignKey constraint specification
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
# Import relationship construct to link Course with User, Instructor, Assignment, and Rubric entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database
from app.core.database import Base


# Database model representing courses and instructional cohorts
class Course(Base):
    """Database model representing academic courses and cohorts.

    Serves as the central organizing container linking enrolled students,
    assignment specifications, evaluation rubrics, and analytics gradebooks.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "courses"

    # Alphanumeric unique identifier for course acting as primary key
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing the authenticated teacher (User) who owns this course
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Foreign key referencing institutional tenant organization
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    # Name or title of the course (e.g. 'Advanced Operating Systems')
    name = Column(String(255), nullable=False)
    # Academic course catalog code (e.g. 'CS-401')
    code = Column(String(64), nullable=False, index=True)
    # Academic section identifier (defaults to 'A')
    section = Column(String(32), nullable=False, default="A")
    # Color tone theme key utilized for UI dashboard badge styling (e.g. lav, blue, sage, amber)
    tone = Column(String(32), default="lav")  # lav, blue, sage, amber
    # Cached student enrollment count for quick dashboard rendering
    students_count = Column(Integer, default=0)
    # Legacy foreign key referencing the instructor entity for backward compatibility
    instructor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True)
    # UTC timestamp when the course record was created
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp when course attributes were last updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Optional soft-deletion timestamp indicating retention in trash bin prior to permanent purge
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    # Many-to-one relationship mapping the teacher (User model)
    teacher = relationship("User", back_populates="courses", foreign_keys=[user_id])
    # Many-to-one relationship mapping tenant organization
    organization = relationship("Organization", back_populates="courses")
    # Many-to-one relationship mapping the legacy assigned instructor
    instructor = relationship("Instructor", back_populates="courses")
    # One-to-many relationship mapping sections configured under this course
    sections = relationship("Section", back_populates="course", cascade="all, delete-orphan")
    # One-to-many relationship mapping student enrollments
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    # One-to-many relationship mapping assignments configured for this course (cascades on delete)
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    # One-to-many relationship mapping rubrics created for this course (cascades on delete)
    rubrics = relationship("Rubric", back_populates="course", cascade="all, delete-orphan")
