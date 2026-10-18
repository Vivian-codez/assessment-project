"""Batch Job database model for Celery background tasks."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from app.core.database import Base


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(String(64), primary_key=True, index=True)
    assignment_id = Column(String(64), nullable=True, index=True)
    job_type = Column(String(64), default="batch_evaluation")

    # Status: queued, processing, completed, failed
    status = Column(String(32), default="queued", index=True)
    progress_pct = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)

    error_message = Column(Text, nullable=True)
    meta_info = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
