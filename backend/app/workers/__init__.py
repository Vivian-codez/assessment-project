# Package docstring explaining Celery asynchronous workers package
"""Celery Workers Package."""

# Import celery_app application instance
from app.workers.celery_app import celery_app

# Export celery_app symbol for worker processes
__all__ = ["celery_app"]
