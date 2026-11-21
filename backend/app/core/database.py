"""Database session management with SQLAlchemy 2.0 and resilient connection pooling.

Provides:
- Persistent QueuePool configuration with pre-ping, pool_recycle, pool_size, and max_overflow
- TCP Keep-Alive parameters for proxy and cloud firewall resilience
- Automatic retry with exponential backoff wrapper (db_retry_with_backoff)
- Transaction-safe SessionLocal sessionmaker and FastAPI get_db dependency
- Comprehensive pool status diagnostics and live connectivity health checks
- Schema initialization and incremental migration utilities
"""

import time
import functools
from typing import Generator, Dict, Any, Callable
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import (
    OperationalError,
    InterfaceError,
    DBAPIError,
    DatabaseError,
    DisconnectionError,
    TimeoutError as SATimeoutError,
)

from app.core.config import settings
from app.core.logging import logger

# Transient exceptions eligible for automatic retry with backoff
TRANSIENT_DB_EXCEPTIONS = (
    OperationalError,
    InterfaceError,
    DBAPIError,
    DatabaseError,
    DisconnectionError,
    SATimeoutError,
    ConnectionResetError,
    ConnectionRefusedError,
    BrokenPipeError,
    TimeoutError,
)


def db_retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.2,
    backoff_factor: float = 2.0,
) -> Callable:
    """Decorator retrying database operations on transient connection drops with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except TRANSIENT_DB_EXCEPTIONS as exc:
                    last_exc = exc
                    logger.warning(
                        f"[DB-RETRY] Transient connection error on attempt {attempt}/{max_retries} "
                        f"in '{func.__name__}': {exc}. Retrying in {delay:.2f}s..."
                    )
                    if attempt == max_retries:
                        logger.error(
                            f"[DB-RETRY] Exceeded max retries ({max_retries}) in '{func.__name__}'. "
                            f"Final error: {exc}"
                        )
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor
            if last_exc:
                raise last_exc
        return wrapper
    return decorator


def _attach_pool_listeners(target_engine):
    """Attach structured event logging listeners to engine connection pool."""
    @event.listens_for(target_engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        logger.info(
            f"[DB-POOL] New physical connection established in pool "
            f"(driver: {target_engine.dialect.name})."
        )

    @event.listens_for(target_engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug("[DB-POOL] Connection checked out from pool.")

    @event.listens_for(target_engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        logger.debug("[DB-POOL] Connection returned to pool.")


# Retrieve the configured database connection URI string
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configure resilient connection engine
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    sqlite_connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        connect_args=sqlite_connect_args,
        echo=False,
    )
    _attach_pool_listeners(engine)
else:
    # PostgreSQL connect arguments with TCP keep-alive options
    pg_connect_args = {
        "connect_timeout": settings.DB_CONNECT_TIMEOUT,
        "keepalives": settings.DB_KEEPALIVES,
        "keepalives_idle": settings.DB_KEEPALIVES_IDLE,
        "keepalives_interval": settings.DB_KEEPALIVES_INTERVAL,
        "keepalives_count": settings.DB_KEEPALIVES_COUNT,
    }
    try:
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            connect_args=pg_connect_args,
            echo=False,
        )
        # Verify socket connectivity with pre-test
        with engine.connect() as conn:
            pass
        _attach_pool_listeners(engine)
    except Exception as pg_err:
        logger.warning(
            f"[DB-INIT] Could not connect to primary PostgreSQL database ({pg_err}). "
            "Falling back to resilient local SQLite storage."
        )
        fallback_url = "sqlite:///./verism.db"
        sqlite_connect_args = {
            "check_same_thread": False,
            "timeout": 30,
        }
        engine = create_engine(
            fallback_url,
            poolclass=QueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            connect_args=sqlite_connect_args,
            echo=False,
        )
        _attach_pool_listeners(engine)

# Create thread-safe session factory bound to the active engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for ORM models
Base = declarative_base()


def get_db_pool_status() -> Dict[str, Any]:
    """Retrieve detailed runtime pool statistics and health parameters."""
    pool = engine.pool
    try:
        size = pool.size() if callable(getattr(pool, "size", None)) else getattr(pool, "_pool_size", 0)
    except Exception:
        size = settings.DB_POOL_SIZE
    try:
        checked_in = pool.checkedin() if callable(getattr(pool, "checkedin", None)) else 0
    except Exception:
        checked_in = 0
    try:
        checked_out = pool.checkedout() if callable(getattr(pool, "checkedout", None)) else 0
    except Exception:
        checked_out = 0
    try:
        overflow = pool.overflow() if callable(getattr(pool, "overflow", None)) else 0
    except Exception:
        overflow = 0

    return {
        "pool_type": pool.__class__.__name__,
        "pool_size": size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle_seconds": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        "pool_timeout_seconds": settings.DB_POOL_TIMEOUT,
        "keepalives_enabled": bool(settings.DB_KEEPALIVES),
        "keepalives_idle_seconds": settings.DB_KEEPALIVES_IDLE,
        "keepalives_interval_seconds": settings.DB_KEEPALIVES_INTERVAL,
        "keepalives_count": settings.DB_KEEPALIVES_COUNT,
    }


def check_db_health() -> Dict[str, Any]:
    """Test live database connectivity with SELECT 1 probe and measure latency."""
    start_time = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "healthy",
            "connected": True,
            "dialect": engine.dialect.name,
            "latency_ms": latency_ms,
            "pool": get_db_pool_status(),
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(f"[DB-HEALTH] Database health check probe failed: {exc}")
        return {
            "status": "unhealthy",
            "connected": False,
            "dialect": engine.dialect.name,
            "error": str(exc),
            "latency_ms": latency_ms,
            "pool": get_db_pool_status(),
        }


@db_retry_with_backoff(max_retries=3, initial_delay=0.2)
def init_db():
    """Create tables and ensure newly added columns are migrated with retry resilience."""
    import app.models  # Ensure all model tables are registered on Base.metadata
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE users ADD COLUMN full_name VARCHAR(255);",
            "ALTER TABLE assignments ADD COLUMN reference_assignment_text TEXT;",
            "ALTER TABLE submissions ADD COLUMN file_content TEXT;",
            "ALTER TABLE submissions ADD COLUMN file_url TEXT;",
            "ALTER TABLE submissions ADD COLUMN content TEXT;",
            "ALTER TABLE submissions ADD COLUMN web_plagiarism_score REAL DEFAULT 0.0;",
            "ALTER TABLE submissions ADD COLUMN web_sources JSON DEFAULT '[]';",
            "ALTER TABLE submissions ADD COLUMN classroom_id VARCHAR(64);",
            "ALTER TABLE submissions ADD COLUMN student_id VARCHAR(64);",
            "ALTER TABLE rubrics ADD COLUMN classroom_id VARCHAR(64);",
            "ALTER TABLE rubrics ADD COLUMN title VARCHAR(255);",
            "ALTER TABLE rubrics ADD COLUMN total_marks REAL DEFAULT 0.0;",
            "ALTER TABLE rubric_criteria ADD COLUMN criterion_name VARCHAR(255);",
            "ALTER TABLE rubric_criteria ADD COLUMN max_points REAL DEFAULT 4.0;",
            "ALTER TABLE rubric_criteria ADD COLUMN levels JSON DEFAULT '[]';",
        ]:
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except Exception:
                pass


# Automatic database schema initialization on startup
try:
    init_db()
except Exception as e:
    logger.warning(f"[DB-INIT] Startup schema migration notice: {e}")


def get_db() -> Generator[Session, None, None]:
    """Dependency yielding a database session with transaction safety and clean pool release.

    Decouples database connection health from request timeouts:
    - Rolls back any aborted transaction state on exception.
    - Cleanly closes the session, releasing the socket back to the pool without severing.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        try:
            db.rollback()
        except Exception as rb_err:
            logger.warning(f"[DB-SESSION] Rollback notice during cleanup: {rb_err}")
        raise exc
    finally:
        try:
            db.close()
        except Exception as cl_err:
            logger.warning(f"[DB-SESSION] Close notice during cleanup: {cl_err}")
