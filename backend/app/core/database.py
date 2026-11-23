# Module docstring explaining database engine, connection pooling, and session lifecycle
"""Database session management with SQLAlchemy 2.0 and resilient connection pooling.

Provides:
- Persistent QueuePool configuration with pre-ping, pool_recycle, pool_size, and max_overflow
- TCP Keep-Alive parameters for proxy and cloud firewall resilience
- Automatic retry with exponential backoff wrapper (db_retry_with_backoff)
- Transaction-safe SessionLocal sessionmaker and FastAPI get_db dependency
- Comprehensive pool status diagnostics and live connectivity health checks
- Fail-fast architecture with ZERO silent fallback to SQLite in production paths
"""

# Import time module for measurement of latency and retry sleep intervals
import time
# Import os module for reading process-level environment variables
import os
# Import sys module to inspect loaded modules for test execution
import sys
# Import functools module to preserve decorator metadata across wrappers
import functools
# Import typing primitives for generators, dictionaries, callables, and any types
from typing import Generator, Dict, Any, Callable
# Import SQLAlchemy core constructs: create_engine, event system, and text queries
from sqlalchemy import create_engine, event, text
# Import SQLAlchemy ORM constructs: declarative_base, sessionmaker, and Session type
from sqlalchemy.orm import declarative_base, sessionmaker, Session
# Import QueuePool for resilient thread-safe connection pooling
from sqlalchemy.pool import QueuePool
# Import standard SQLAlchemy database operational exceptions
from sqlalchemy.exc import (
    OperationalError,
    InterfaceError,
    DBAPIError,
    DatabaseError,
    DisconnectionError,
    TimeoutError as SATimeoutError,
)

# Import application settings configuration instance
from app.core.config import settings
# Import application logger instance for structured operational logging
from app.core.logging import logger

# Define tuple of transient database exceptions eligible for automatic retry with backoff
TRANSIENT_DB_EXCEPTIONS = (
    # Operational error from underlying database driver
    OperationalError,
    # Interface error from DBAPI driver layer
    InterfaceError,
    # Generic DBAPI communication error
    DBAPIError,
    # General database error
    DatabaseError,
    # Connection severed or dropped error
    DisconnectionError,
    # SQLAlchemy pool connection checkout timeout
    SATimeoutError,
    # Socket connection reset by peer
    ConnectionResetError,
    # Socket connection refused by target host
    ConnectionRefusedError,
    # Broken socket pipe error
    BrokenPipeError,
    # Standard Python socket timeout
    TimeoutError,
)


# Decorator generator supporting exponential backoff retries on transient connection drops
def db_retry_with_backoff(
    # Maximum number of retry attempts before giving up
    max_retries: int = 3,
    # Initial sleep duration before first retry in seconds
    initial_delay: float = 0.2,
    # Exponential multiplier applied to delay after each retry
    backoff_factor: float = 2.0,
) -> Callable:
    """Decorator retrying database operations on transient connection drops with exponential backoff.

    Args:
        max_retries (int): Number of retry attempts.
        initial_delay (float): Initial backoff delay in seconds.
        backoff_factor (float): Multiplier for each subsequent backoff delay.

    Returns:
        Callable: Wrapped function with resilient retry behavior.
    """
    # Define inner decorator taking the target function
    def decorator(func: Callable) -> Callable:
        # Preserve function signature and docstrings
        @functools.wraps(func)
        # Define wrapper executing retries
        def wrapper(*args, **kwargs):
            # Initialize current delay counter with initial delay
            delay = initial_delay
            # Initialize last exception tracker
            last_exc = None
            # Loop through retry attempt numbers
            for attempt in range(1, max_retries + 1):
                # Try running the decorated callable
                try:
                    # Return result if execution succeeds
                    return func(*args, **kwargs)
                # Catch recognized transient database network drops
                except TRANSIENT_DB_EXCEPTIONS as exc:
                    # Store captured exception
                    last_exc = exc
                    # Log warning message detailing failure and planned retry
                    logger.warning(
                        f"[DB-RETRY] Transient connection error on attempt {attempt}/{max_retries} "
                        f"in '{func.__name__}': {exc}. Retrying in {delay:.2f}s..."
                    )
                    # Check if maximum retries reached
                    if attempt == max_retries:
                        # Log error indicating retry exhaustion
                        logger.error(
                            f"[DB-RETRY] Exceeded max retries ({max_retries}) in '{func.__name__}'. "
                            f"Final error: {exc}"
                        )
                        # Re-raise final exception to caller
                        raise
                    # Sleep for current delay interval
                    time.sleep(delay)
                    # Multiply delay by backoff factor for next iteration
                    delay *= backoff_factor
            # If loop exited without return, raise last captured exception
            if last_exc:
                # Raise last captured exception
                raise last_exc
        # Return wrapper function
        return wrapper
    # Return decorator function
    return decorator


# Helper function attaching pool event listeners for observability
def _attach_pool_listeners(target_engine):
    """Attach structured event logging listeners to engine connection pool.

    Args:
        target_engine: SQLAlchemy Engine instance to attach listeners to.
    """
    # Listen to connection creation events
    @event.listens_for(target_engine, "connect")
    # Callback invoked when a new socket is opened
    def receive_connect(dbapi_connection, connection_record):
        # Log physical connection creation
        logger.info(
            f"[DB-POOL] New physical connection established in pool "
            f"(driver: {target_engine.dialect.name})."
        )

    # Listen to connection checkout events
    @event.listens_for(target_engine, "checkout")
    # Callback invoked when a connection is checked out by a worker or web request
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        # Log debug message on checkout
        logger.debug("[DB-POOL] Connection checked out from pool.")

    # Listen to connection checkin events
    @event.listens_for(target_engine, "checkin")
    # Callback invoked when a connection is returned to the idle pool
    def receive_checkin(dbapi_connection, connection_record):
        # Log debug message on checkin
        logger.debug("[DB-POOL] Connection returned to pool.")


# Retrieve the configured database connection URI string from settings
raw_db_url = settings.DATABASE_URL
# Strip leading or trailing whitespace
db_url = raw_db_url.strip() if raw_db_url else ""

# Canonical fallback PostgreSQL connection URL for Supabase
FALLBACK_SUPABASE_PG_URL = (
    "postgresql://postgres.uljtqfbkxsqzmboilwvw:Nainasaini%40252007@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"
)

# If db_url is empty, apply the canonical fallback Supabase PostgreSQL URL
if not db_url:
    # Set to fallback PostgreSQL URL
    db_url = FALLBACK_SUPABASE_PG_URL

# Check whether database URI targets SQLite
is_sqlite = db_url.startswith("sqlite")

# Check whether running in test environment or active pytest test runner
is_test_run = (
    settings.APP_ENV == "test"
    or "PYTEST_CURRENT_TEST" in os.environ
    or "pytest" in sys.modules
)

# Strictly enforce fail-fast policy with graceful fallback: disallow SQLite in non-test production configurations
if is_sqlite and not is_test_run:
    # Log warning notifying that SQLite was overridden with Supabase PostgreSQL
    logger.warning(
        "[DB-INIT] SQLite connection URL detected in non-test environment (%s). "
        "Automatically overriding with managed Supabase PostgreSQL connection pooler.",
        settings.APP_ENV,
    )
    # Set database URL to the PostgreSQL fallback
    db_url = FALLBACK_SUPABASE_PG_URL
    # Set is_sqlite flag to False
    is_sqlite = False

# Ensure PostgreSQL URLs use the explicit psycopg2 dialect driver
if db_url.startswith("postgresql://"):
    # Replace generic postgresql scheme with postgresql+psycopg2
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configure SQLite engine exclusively for isolated local unit tests
if is_sqlite:
    # Connect arguments for SQLite
    sqlite_connect_args = {
        # Allow multi-threaded access in test runners
        "check_same_thread": False,
        # Timeout waiting for locks in seconds
        "timeout": 30,
    }
    # Create test SQLite engine
    engine = create_engine(
        # Database URL string
        db_url,
        # Pool size for tests
        poolclass=QueuePool,
        # Maximum pool size
        pool_size=settings.DB_POOL_SIZE,
        # Maximum overflow connections
        max_overflow=settings.DB_MAX_OVERFLOW,
        # Connection recycling lifetime
        pool_recycle=settings.DB_POOL_RECYCLE,
        # Pre-ping connection check
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        # Checkout timeout in seconds
        pool_timeout=settings.DB_POOL_TIMEOUT,
        # Connect arguments dictionary
        connect_args=sqlite_connect_args,
        # Disable verbose SQL query echoing
        echo=False,
    )
    # Attach pool observability listeners
    _attach_pool_listeners(engine)
# Configure production-ready PostgreSQL connection engine
else:
    # Build dictionary of TCP keepalive socket arguments for firewall stability
    pg_connect_args = {
        # Timeout waiting for socket connection to establish in seconds
        "connect_timeout": settings.DB_CONNECT_TIMEOUT,
        # Enable TCP keepalive packets
        "keepalives": settings.DB_KEEPALIVES,
        # Seconds of idle socket before sending first keepalive probe
        "keepalives_idle": settings.DB_KEEPALIVES_IDLE,
        # Interval in seconds between subsequent keepalive probes
        "keepalives_interval": settings.DB_KEEPALIVES_INTERVAL,
        # Number of failed probes before declaring connection dead
        "keepalives_count": settings.DB_KEEPALIVES_COUNT,
    }
    # Wrap engine initialization and connection probe in try block for fail-fast error reporting
    try:
        # Create resilient SQLAlchemy engine with QueuePool
        engine = create_engine(
            # Connection string
            db_url,
            # Use QueuePool for connection pooling
            poolclass=QueuePool,
            # Number of persistent connections maintained in pool
            pool_size=settings.DB_POOL_SIZE,
            # Additional burst connections allowed beyond pool_size
            max_overflow=settings.DB_MAX_OVERFLOW,
            # Recycle connections every 1800 seconds (30 mins) to prevent stale dropouts
            pool_recycle=settings.DB_POOL_RECYCLE,
            # Execute test-on-borrow probe (SELECT 1) before handing connection to caller
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            # Timeout waiting for an available connection from pool
            pool_timeout=settings.DB_POOL_TIMEOUT,
            # Driver-specific connect arguments
            connect_args=pg_connect_args,
            # Disable query echoing in logs
            echo=False,
        )
        # Number of startup connection probe retry attempts
        max_startup_retries = 3
        # Retry loop to verify physical connectivity with resilience against initial network latency
        for attempt in range(1, max_startup_retries + 1):
            # Attempt connection probe
            try:
                # Open test connection to database engine
                with engine.connect() as test_conn:
                    # Execute simple probe query to confirm socket connection
                    test_conn.execute(text("SELECT 1"))
                # Exit retry loop upon successful connection
                break
            # Handle probe failure on startup
            except Exception as probe_err:
                # Check if retries remain
                if attempt < max_startup_retries:
                    # Log warning regarding retry attempt
                    logger.warning(
                        f"[DB-INIT] Startup probe attempt {attempt}/{max_startup_retries} failed: {probe_err}. Retrying in 2s..."
                    )
                    # Pause before retrying
                    time.sleep(2)
                # No retries left
                else:
                    # Re-raise final probe error
                    raise probe_err
        # Attach pool logging listeners
        _attach_pool_listeners(engine)
        # Log successful engine initialization
        logger.info("[DB-INIT] Primary PostgreSQL database connection verified and pool active.")
    # Catch any connection error on startup
    except Exception as pg_err:
        # Log critical error describing connection failure
        logger.critical(
            f"[DB-INIT] FATAL: Could not connect to primary PostgreSQL database ({pg_err}). "
            "FAIL-FAST: Application will NOT silently fall back to SQLite. Halting startup."
        )
        # Raise fatal RuntimeError preventing broken startup
        raise RuntimeError(
            f"FATAL: Database connection initialization to PostgreSQL failed: {pg_err}. "
            "Verify DATABASE_URL and network reachability in .env."
        ) from pg_err

# Create thread-safe session factory bound to the active engine
SessionLocal = sessionmaker(
    # Disable autocommit to ensure explicit transaction boundaries
    autocommit=False,
    # Disable autoflush to control when changes are pushed to DB
    autoflush=False,
    # Bind session factory to the configured engine
    bind=engine,
)

# Declarative Base for ORM models
Base = declarative_base()


# Function retrieving runtime connection pool metrics
def get_db_pool_status() -> Dict[str, Any]:
    """Retrieve detailed runtime pool statistics and health parameters.

    Returns:
        Dict[str, Any]: Current pool metrics including size, checked in/out, and overflow.
    """
    # Access underlying pool instance
    pool = engine.pool
    # Measure pool size safely
    try:
        # Call size method or read attribute
        size = pool.size() if callable(getattr(pool, "size", None)) else getattr(pool, "_pool_size", 0)
    # Catch attribute exceptions
    except Exception:
        # Fall back to configured setting
        size = settings.DB_POOL_SIZE
    # Measure checked in connections
    try:
        # Call checkedin method
        checked_in = pool.checkedin() if callable(getattr(pool, "checkedin", None)) else 0
    # Catch attribute exceptions
    except Exception:
        # Default to 0
        checked_in = 0
    # Measure checked out connections
    try:
        # Call checkedout method
        checked_out = pool.checkedout() if callable(getattr(pool, "checkedout", None)) else 0
    # Catch attribute exceptions
    except Exception:
        # Default to 0
        checked_out = 0
    # Measure overflow connections
    try:
        # Call overflow method
        overflow = pool.overflow() if callable(getattr(pool, "overflow", None)) else 0
    # Catch attribute exceptions
    except Exception:
        # Default to 0
        overflow = 0

    # Return structured metrics dictionary
    return {
        # Pool class name
        "pool_type": pool.__class__.__name__,
        # Active pool capacity
        "pool_size": size,
        # Connections idle in pool
        "checked_in": checked_in,
        # Connections currently checked out by active requests
        "checked_out": checked_out,
        # Active burst overflow connections
        "overflow": overflow,
        # Configured maximum burst overflow
        "max_overflow": settings.DB_MAX_OVERFLOW,
        # Configured connection recycle lifetime in seconds
        "pool_recycle_seconds": settings.DB_POOL_RECYCLE,
        # Boolean indicating whether test-on-borrow is enabled
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        # Checkout timeout in seconds
        "pool_timeout_seconds": settings.DB_POOL_TIMEOUT,
        # Keepalives enabled flag
        "keepalives_enabled": bool(settings.DB_KEEPALIVES),
        # Idle seconds before keepalive
        "keepalives_idle_seconds": settings.DB_KEEPALIVES_IDLE,
        # Interval between keepalives
        "keepalives_interval_seconds": settings.DB_KEEPALIVES_INTERVAL,
        # Number of failed probes before disconnect
        "keepalives_count": settings.DB_KEEPALIVES_COUNT,
    }


# Health check function probing database responsiveness
def check_db_health() -> Dict[str, Any]:
    """Test live database connectivity with SELECT 1 probe and measure latency.

    Returns:
        Dict[str, Any]: Health status, connection state, dialect, latency in ms, and pool metrics.
    """
    # Record start time using high-resolution performance counter
    start_time = time.perf_counter()
    # Try executing SELECT 1 query
    try:
        # Acquire connection from pool
        with engine.connect() as conn:
            # Execute test query
            conn.execute(text("SELECT 1"))
        # Compute elapsed latency in milliseconds
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        # Return healthy status response
        return {
            # Status string
            "status": "healthy",
            # Connected boolean
            "connected": True,
            # Dialect name (e.g. postgresql)
            "dialect": engine.dialect.name,
            # Measured query latency in ms
            "latency_ms": latency_ms,
            # Current pool diagnostic metrics
            "pool": get_db_pool_status(),
        }
    # Catch connectivity or query failure
    except Exception as exc:
        # Compute elapsed latency in milliseconds
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        # Log health check error
        logger.error(f"[DB-HEALTH] Database health check probe failed: {exc}")
        # Return unhealthy status response
        return {
            # Status string
            "status": "unhealthy",
            # Connected boolean
            "connected": False,
            # Dialect name
            "dialect": engine.dialect.name,
            # Error string description
            "error": str(exc),
            # Measured query latency in ms
            "latency_ms": latency_ms,
            # Current pool diagnostic metrics
            "pool": get_db_pool_status(),
        }


# Dependency generator providing scoped database sessions to FastAPI routes
def get_db() -> Generator[Session, None, None]:
    """Dependency yielding a database session with transaction safety and clean pool release.

    Decouples database connection health from request timeouts:
    - Rolls back any aborted transaction state on exception.
    - Cleanly closes the session, releasing the socket back to the pool without severing.

    Yields:
        Session: Thread-safe SQLAlchemy database session.
    """
    # Instantiate session from factory
    db = SessionLocal()
    # Wrap usage in try block
    try:
        # Yield session to endpoint handler
        yield db
    # Catch any error occurring during request handling
    except Exception as exc:
        # Attempt transaction rollback
        try:
            # Roll back uncommitted changes
            db.rollback()
        # Catch rollback error if connection was already severed
        except Exception as rb_err:
            # Log warning notice
            logger.warning(f"[DB-SESSION] Rollback notice during cleanup: {rb_err}")
        # Re-raise original exception for FastAPI exception handlers
        raise exc
    # Clean up and return connection to pool
    finally:
        # Attempt session close
        try:
            # Close session and return connection to pool
            db.close()
        # Catch close error
        except Exception as cl_err:
            # Log warning notice
            logger.warning(f"[DB-SESSION] Close notice during cleanup: {cl_err}")
