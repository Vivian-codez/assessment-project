"""Celery Application Initialization and Broker Configuration."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "verism_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.evaluation_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour maximum for massive batches
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

import sys

if sys.platform == "win32":
    # Windows does not support prefork pool; set solo pool as default
    celery_app.conf.worker_pool = "solo"

# Ensure all database tables exist on worker initialization
from app.core.database import Base, engine
import app.models  # noqa: F401

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass



