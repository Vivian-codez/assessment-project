# Module docstring explaining Celery application initialization, queue segregation, and broker configuration
"""Celery Application Initialization and Broker Configuration.

Implements Phase 4 segregated queue architecture:
- extract: Fast text/code/docx/xlsx extraction
- ocr: Images/scanned PDFs (CPU-heavy, lower concurrency)
- grade: Gemini API evaluation calls (I/O-bound, high concurrency)
- similarity: Deterministic winnowing, shingling, embeddings
- export: Gradebook and case report generation
"""

# Import the main Celery application class from celery
from celery import Celery
# Import kombu Queue and Exchange constructs for fine-grained queue routing
from kombu import Exchange, Queue
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

# Define standard direct exchange for evaluation pipeline
default_exchange = Exchange("verism", type="direct")

# Define segregated queues
task_queues = [
    # Fast text/code extraction queue
    Queue("extract", default_exchange, routing_key="task.extract"),
    # CPU-heavy OCR queue for scanned documents and images
    Queue("ocr", default_exchange, routing_key="task.ocr"),
    # High-concurrency I/O-bound autograding queue for Gemini API calls
    Queue("grade", default_exchange, routing_key="task.grade"),
    # Deterministic winnowing and similarity queue
    Queue("similarity", default_exchange, routing_key="task.similarity"),
    # Asynchronous gradebook and report export queue
    Queue("export", default_exchange, routing_key="task.export"),
]

# Configure task routing table mapping specific task names to their respective queues
task_routes = {
    # Route fast document/text extraction task to extract queue
    "app.workers.evaluation_tasks.extract_submission_task": {"queue": "extract", "routing_key": "task.extract"},
    # Route OCR document extraction task to ocr queue
    "app.workers.evaluation_tasks.ocr_submission_task": {"queue": "ocr", "routing_key": "task.ocr"},
    # Route individual submission grading task to grade queue
    "app.workers.evaluation_tasks.grade_submission_task": {"queue": "grade", "routing_key": "task.grade"},
    # Route batch evaluation orchestrator to grade queue
    "app.workers.evaluation_tasks.evaluate_batch_task": {"queue": "grade", "routing_key": "task.grade"},
    # Route similarity checks to similarity queue
    "app.workers.evaluation_tasks.similarity_check_task": {"queue": "similarity", "routing_key": "task.similarity"},
    # Route gradebook export tasks to export queue
    "app.workers.evaluation_tasks.export_gradebook_task": {"queue": "export", "routing_key": "task.export"},
}

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
    # Acknowledge tasks late (after execution) to prevent message loss on worker crash
    task_acks_late=True,
    # Reject task on worker loss so message is requeued (dead-letter / retry safety)
    task_reject_on_worker_lost=True,
    # Soft execution time limit (warning emitted after 300 seconds)
    task_soft_time_limit=300,
    # Enforce a hard execution time limit of 600 seconds per task
    task_time_limit=600,
    # Set prefetch multiplier to 1 so workers reserve only one message at a time
    worker_prefetch_multiplier=1,
    # Restart child worker processes after 50 tasks to prevent memory leaks
    worker_max_tasks_per_child=50,
    # Register segregated queues configuration
    task_queues=task_queues,
    # Register task routing configuration
    task_routes=task_routes,
    # Default queue name
    task_default_queue="grade",
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
    celery_app.conf.worker_pool = "solo"

# Import SQLAlchemy declarative Base and database engine
from app.core.database import Base, engine
# Import all models to ensure their table definitions are registered on Base.metadata
import app.models  # noqa: F401

# Begin a try block to safely create database tables without crashing if already present
try:
    # Create all registered database tables in the PostgreSQL database if they do not exist
    Base.metadata.create_all(bind=engine)
# Catch any database connection or initialization exceptions silently
except Exception:
    # Ignore errors during table creation
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
