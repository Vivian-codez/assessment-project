# Module docstring explaining DeletionRequest database entity for FERPA/GDPR right-to-be-forgotten compliance
"""DeletionRequest database model tracking data deletion and erasure audits."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, text, and foreign keys
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model tracking student record erasure and GDPR/FERPA deletion compliance requests
class DeletionRequest(Base):
    """Database model logging data deletion requests and audit compliance.

    Maintains immutable compliance logs whenever student records, submissions,
    or grades are purged pursuant to institutional retention policies.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "deletion_requests"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing requesting user
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Classification of target entity removed ('Student', 'Submission', 'Course', 'Rubric')
    entity_type = Column(String(64), nullable=False)
    # Unique identifier of entity that was deleted
    entity_id = Column(String(64), nullable=False)
    # Status of the deletion workflow ('pending', 'completed', 'rejected')
    status = Column(String(32), default="completed", nullable=False)
    # Justification or compliance rationale provided for the deletion
    reason = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp when deletion was requested
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Timezone-aware UTC timestamp when purge was completed
    completed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the user who initiated the deletion
    requester = relationship("User", backref="deletion_requests")

