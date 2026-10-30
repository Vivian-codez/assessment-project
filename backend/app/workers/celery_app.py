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
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    result_backend_max_retries=1,
    redis_socket_connect_timeout=1.0,
    redis_socket_timeout=1.0,
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


def is_redis_available() -> bool:
    """Checks whether the Redis broker is reachable with an aggressive 0.2s timeout."""
    try:
        import redis
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        return bool(client.ping())
    except Exception:
        return False



