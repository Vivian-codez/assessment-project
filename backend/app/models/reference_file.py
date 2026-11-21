# Module docstring explaining ReferenceFile database entity for ground truth exemplars
"""ReferenceFile database model for teacher reference solutions and benchmarking files."""

# Import uuid library to generate unique random string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, text, and foreign keys
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model storing teacher reference solution files, answer keys, and benchmarking exemplars
class ReferenceFile(Base):
    """Database model storing reference solution files and ground truth exemplars.

    Grounds AI auto-grading prompts with authentic teacher solutions,
    code implementations, and sample output specifications.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "reference_files"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent assignment
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    # Original filename of the reference solution file
    file_name = Column(String(255), nullable=False)
    # Filesystem storage relative or absolute path on disk
    file_path = Column(String(512), nullable=True)
    # Download URL for client web preview
    file_url = Column(String(1024), nullable=True)
    # Clean text extracted from reference document by parsing pipeline
    extracted_text = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when reference file was uploaded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent assignment entity
    assignment = relationship("Assignment", backref="reference_files")

