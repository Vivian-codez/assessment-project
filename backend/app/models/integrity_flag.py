# Module docstring explaining IntegrityFlag database entity for academic honesty review
"""IntegrityFlag database model representing academic honesty concerns and anomalies."""

# Import uuid library to generate unique string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, booleans, text, JSON, and foreign keys
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing academic integrity flags raised on student submissions
class IntegrityFlag(Base):
    """Database model tracking academic integrity concerns and anomalies.

    Enforces teacher-in-the-loop audit workflows for peer-to-peer collisions,
    external web sources, and AI generation probabilities.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "integrity_flags"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing flagged submission entity
    submission_id = Column(String(64), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    # Categorical classification of the integrity concern (e.g. 'peer_collision', 'web_plagiarism', 'ai_indicator')
    flag_type = Column(String(64), nullable=False, index=True)
    # Severity assessment level ('low', 'medium', 'high', 'critical')
    severity = Column(String(32), default="medium", nullable=False)
    # Human-readable descriptive explanation of why the flag was triggered
    description = Column(Text, nullable=False)
    # Structured evidence payload containing matching URLs, collision pairs, or probability vectors
    details = Column(JSON, default=dict, nullable=False)
    # Lifecycle review status for the integrity flag: new, reviewing, cleared, confirmed
    status = Column(String(32), default="new", nullable=False, index=True)
    # Resolution status flag indicating whether an educator has reviewed and decided the flag
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    # Optional foreign key referencing educator who resolved the flag
    resolved_by = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Official resolution rationale and meeting notes recorded by instructor
    resolution_note = Column(Text, nullable=True)
    # Timezone-aware UTC timestamp recording when flag was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the parent submission
    submission = relationship("Submission", backref="integrity_flags")
    # Many-to-one relationship mapping the educator who resolved the flag
    resolver = relationship("User", backref="resolved_flags")

