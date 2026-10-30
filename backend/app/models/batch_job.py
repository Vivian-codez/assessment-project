# Module docstring explaining that this file defines the Batch Job database model for Celery background tasks
"""Batch Job database model for Celery background tasks."""

# Import datetime utility for timestamp tracking
from datetime import datetime
# Import SQLAlchemy column types for string, numbers, dates, text, and JSON data
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
# Import the shared declarative base class for database models
from app.core.database import Base


# Define the BatchJob model representing asynchronous background tasks
class BatchJob(Base):
    # Specify the database table name where batch job records are stored
    __tablename__ = "batch_jobs"

    # Unique string identifier for the batch job, configured as the primary key and indexed for lookups
    id = Column(String(64), primary_key=True, index=True)
    # Optional foreign identifier linking this batch job to a specific assignment
    assignment_id = Column(String(64), nullable=True, index=True)
    # Classification string for the job type, defaulting to batch_evaluation
    job_type = Column(String(64), default="batch_evaluation")

    # Current execution status of the job (e.g., queued, processing, completed, failed), indexed for filtering
    status = Column(String(32), default="queued", index=True)
    # Percentage representation of job completion from 0.0 to 100.0
    progress_pct = Column(Float, default=0.0)
    # Total count of items or submissions scheduled to be processed in this job
    total_items = Column(Integer, default=0)
    # Count of items or submissions successfully or attemptedly processed so far
    processed_items = Column(Integer, default=0)

    # Detailed error message string if the background job encounters a failure
    error_message = Column(Text, nullable=True)
    # Flexible JSON field storing arbitrary metadata, parameters, and logs for the job
    meta_info = Column(JSON, default=dict)

    # Timestamp recording when this batch job record was initially created
    created_at = Column(DateTime, default=datetime.utcnow)
    # Timestamp recording when this batch job record was last modified, auto-updating on changes
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
