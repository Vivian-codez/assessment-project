# Module docstring explaining the purpose of this file: Celery application initialization and broker configuration
"""Celery Application Initialization and Broker Configuration."""

# Import the main Celery application class from the celery library
from celery import Celery
# Import application settings instance containing Redis broker and backend configuration URLs
from app.core.config import settings

# Instantiate the Celery application with worker name and configured broker/backend endpoints
celery_app = Celery(
    # Set the registered name of the Celery worker application
    "verism_worker",
    # Set the broker URL pointing to Redis from application settings
    broker=settings.CELERY_BROKER_URL,
    # Set the result backend URL pointing to Redis from application settings
    backend=settings.CELERY_RESULT_BACKEND,
    # Register the worker evaluation tasks module so Celery can discover available tasks
    include=["app.workers.evaluation_tasks"],
)

# Configure Celery operational and performance parameters
celery_app.conf.update(
    # Specify JSON as the serialization format for task payloads
    task_serializer="json",
    # Configure accepted content types for incoming task messages
    accept_content=["json"],
    # Specify JSON as the serialization format for task return results
    result_serializer="json",
    # Define Coordinated Universal Time (UTC) as the default worker timezone
    timezone="UTC",
    # Enforce UTC timestamping for all scheduled and tracked tasks
    enable_utc=True,
    # Record and emit the STARTED state event when a worker begins executing a task
    task_track_started=True,
    # Enforce a hard execution time limit of 3600 seconds (1 hour) per task
    task_time_limit=3600,  # 1 hour maximum for massive batches
    # Set prefetch multiplier to 1 so workers reserve only one message at a time
    worker_prefetch_multiplier=1,
    # Restart child worker processes after 50 tasks to prevent memory leaks
    worker_max_tasks_per_child=50,
    # Disable connection retries during worker startup to fail fast if Redis is down
    broker_connection_retry_on_startup=False,
    # Limit broker connection retry attempts to a single attempt
    broker_connection_max_retries=1,
    # Limit result backend connection retry attempts to a single attempt
    result_backend_max_retries=1,
    # Set socket connection timeout to 1.0 second for Redis connections
    redis_socket_connect_timeout=1.0,
    # Set socket read/write timeout to 1.0 second for Redis operations
    redis_socket_timeout=1.0,
)

# Import the sys module to detect the host operating system platform
import sys

# Check if the host operating system is Windows (win32)
if sys.platform == "win32":
    # Set worker execution pool to 'solo' since Windows lacks POSIX fork support
    # Windows does not support prefork pool; set solo pool as default
    celery_app.conf.worker_pool = "solo"

# Import SQLAlchemy declarative Base and database engine
# Ensure all database tables exist on worker initialization
from app.core.database import Base, engine
# Import all models to ensure their table definitions are registered on Base.metadata
import app.models  # noqa: F401

# Begin a try block to safely create database tables without crashing if already present
try:
    # Create all registered database tables in the PostgreSQL database if they do not exist
    Base.metadata.create_all(bind=engine)
# Catch any database connection or initialization exceptions silently
except Exception:
    # Ignore errors during table creation (e.g. if database is unavailable or tables exist)
    pass


# Define a helper function to verify if the Redis broker is reachable
def is_redis_available() -> bool:
    # Docstring explaining Redis availability check with short timeout
    """Checks whether the Redis broker is reachable with an aggressive 0.2s timeout."""
    # Begin try block to handle Redis connection attempts
    try:
        # Import the redis client library dynamically
        import redis
        # Instantiate a Redis client with a quick 0.2 second connection and socket timeout
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        # Ping the Redis server and return True if response is received
        return bool(client.ping())
    # Catch any connection errors or timeout exceptions
    except Exception:
        # Return False when Redis cannot be reached
        return False
