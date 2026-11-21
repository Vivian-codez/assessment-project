# Module docstring explaining SubmissionFile database entity for multi-file submissions
"""SubmissionFile database model representing individual uploaded files in a submission."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, numbers, text, and foreign keys
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Text
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing individual uploaded files within a student's submission bundle
class SubmissionFile(Base):
    """Database model storing individual file artifacts within a student submission.

    Supports multi-file and composite project submissions (e.g. source code files,
    report PDF, screenshots, data files) attached to a single submission entity.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "submission_files"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent submission entity
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Original filename of the uploaded artifact
    file_name = Column(String(255), nullable=False)
    # Storage filesystem relative or absolute path on disk
    file_path = Column(String(512), nullable=True)
    # Public or signed download URL for frontend client viewing
    file_url = Column(String(1024), nullable=True)
    # File format extension or MIME classification
    file_type = Column(String(64), default="pdf", nullable=False)
    # Exact byte size of the uploaded file
    file_size_bytes = Column(BigInteger, nullable=True)
    # Text extracted from this specific file artifact
    extracted_text = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when file artifact was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent submission bundle
    submission = relationship("Submission", backref="files")

