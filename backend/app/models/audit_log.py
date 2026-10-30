# Module docstring explaining that this file defines the Audit Log database model for compliance and activity tracking
"""Audit Log database model for FERPA/GDPR compliance and teacher action tracking."""

# Import datetime utility for timestamp tracking
from datetime import datetime
# Import SQLAlchemy column types and foreign key constraint for database mapping
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
# Import relationship utility for object relational mapping between tables
from sqlalchemy.orm import relationship

# Import the shared declarative base class for database models
from app.core.database import Base


# Define the AuditLog model representing immutable compliance and activity audit records
class AuditLog(Base):
    # Specify the database table name where audit log entries are persisted
    __tablename__ = "audit_logs"

    # Unique string identifier for the audit log record, configured as the primary key and indexed for fast retrieval
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing the instructor who performed the action, set to NULL if instructor is deleted
    actor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True)
    # Human-readable name of the acting user or service, defaulting to 'System'
    actor_name = Column(String(255), default="System")

    # Name or category of the action executed (e.g., login, grade_override, ferpa_access), indexed for queries
    action = Column(String(64), nullable=False, index=True)
    # The classification or model name of the target entity (e.g., submission, grade, course)
    entity_type = Column(String(64), nullable=False)
    # The unique identifier of the specific target entity affected by the action
    entity_id = Column(String(64), nullable=False)

    # Detailed JSON payload capturing context, old vs new values, or operational metadata
    details = Column(JSON, default=dict)
    # IP address of the client device that triggered the action for security auditing
    ip_address = Column(String(64), nullable=True)
    # UTC timestamp when the audit event occurred, indexed for chronological time-range queries
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Establish an ORM relationship pointing back to the Instructor model associated with this audit entry
    actor = relationship("Instructor", back_populates="audit_logs")
