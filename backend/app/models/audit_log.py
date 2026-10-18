"""Audit Log database model for FERPA/GDPR compliance and teacher action tracking."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    actor_id = Column(String(64), ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True)
    actor_name = Column(String(255), default="System")

    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)

    details = Column(JSON, default=dict)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    actor = relationship("Instructor", back_populates="audit_logs")
