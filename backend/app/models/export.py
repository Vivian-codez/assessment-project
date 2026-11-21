# Module docstring explaining Export database entity for reporting and gradebook downloads
"""Export database model tracking generated reports and gradebook archives."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, and foreign keys
from sqlalchemy import Column, String, DateTime, ForeignKey
# Import ORM relationship utility
from sqlalchemy.orm import relationship, backref

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model tracking generated analytical gradebooks and compliance export artifacts
class Export(Base):
    """Database model tracking analytical and gradebook exports.

    Records CSV gradebooks, PDF audit reports, and FERPA-compliant student
    assessment packages generated for institutional archival.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "exports"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing parent course
    course_id = Column(String(64), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    # Foreign key referencing educator requesting export
    requested_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Format classification ('csv_gradebook', 'pdf_integrity_audit', 'lms_canvas_sync')
    export_type = Column(String(64), nullable=False)
    # Filesystem storage relative or absolute path on disk
    file_path = Column(String(512), nullable=True)
    # Download URL for client retrieval
    file_url = Column(String(1024), nullable=True)
    # Generation execution status ('pending', 'processing', 'completed', 'failed')
    status = Column(String(32), default="pending", nullable=False)
    # Timezone-aware UTC timestamp when export was generated
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent course with cascade on delete
    course = relationship("Course", backref=backref("exports", cascade="all, delete-orphan", passive_deletes=True))
    # Many-to-one relationship mapping the requesting user
    requester = relationship("User", backref="exports")

