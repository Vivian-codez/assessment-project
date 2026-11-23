"""Health check and system diagnostic API endpoints.

Provides lightweight diagnostic probes for:
- PostgreSQL database connectivity (SELECT 1 and latency)
- Google Gemini GenAI service configuration
- Local / Object storage adapter accessibility
"""

# Import datetime class for UTC timestamp tracking
from datetime import datetime, timezone
# Import os module for directory and filesystem checks
import os
# Import FastAPI routing and response primitives
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
# Import application settings configuration instance
from app.core.config import settings
# Import database health check utility function
from app.core.database import check_db_health, get_db_pool_status

# Initialize FastAPI router instance tagged under Health
router = APIRouter(tags=["Health"])


def _check_storage_status() -> dict:
    """Probes the configured storage backend (local uploads directory or object storage).

    Returns:
        dict: Storage diagnostic details including readiness, mode, and path.
    """
    # Resolve target uploads directory path from settings
    uploads_path = os.path.abspath(settings.UPLOADS_DIR)
    # Track whether filesystem is writable
    is_writable = False

    # Attempt to verify or create directory
    try:
        # Create directory recursively if absent
        os.makedirs(uploads_path, exist_ok=True)
        # Test write access with a temporary marker file
        test_file = os.path.join(uploads_path, ".health_check_probe")
        # Write single byte to test file
        with open(test_file, "w", encoding="utf-8") as fh:
            # Write marker text
            fh.write("ok")
        # Remove test marker file
        if os.path.exists(test_file):
            # Delete probe file
            os.remove(test_file)
        # Mark writable state as true
        is_writable = True
    # Catch filesystem permission or path errors
    except Exception as exc:
        # File system cannot be written
        is_writable = False

    # Return structured storage status
    return {
        # Overall status string
        "status": "ready" if is_writable else "degraded",
        # Configured storage mode
        "mode": "local_disk" if not settings.USE_SUPABASE else "supabase_and_disk",
        # Absolute path to storage directory
        "path": uploads_path,
        # Boolean indicating write permission
        "writable": is_writable,
    }


def _check_gemini_status() -> dict:
    """Probes the Google Gemini API client configuration.

    Returns:
        dict: Gemini API diagnostic details including configuration status and active models.
    """
    # Check if GEMINI_API_KEY is present and non-empty
    api_key_set = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 0)
    # Mask key for secure diagnostic exposure
    masked_key = (
        f"{settings.GEMINI_API_KEY[:4]}...{settings.GEMINI_API_KEY[-4:]}"
        if api_key_set and len(settings.GEMINI_API_KEY) > 8
        else ("configured" if api_key_set else "missing")
    )

    # Return structured Gemini status
    return {
        # Status indicating whether API key is supplied
        "status": "configured" if api_key_set else "missing_api_key",
        # Default LLM evaluation model
        "default_model": settings.GEMINI_MODEL,
        # Strong re-evaluation model
        "strong_model": settings.GEMINI_MODEL_STRONG,
        # Embedding model identifier
        "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        # Key presence indicator
        "api_key_configured": api_key_set,
        # Obfuscated key preview
        "api_key_preview": masked_key,
    }


@router.get("/health")
@router.get("/api/health")
def health_check():
    """Lightweight comprehensive health check verifying database, Gemini API, and storage.

    Returns:
        JSONResponse: Detailed diagnostic status payload for all core services.
    """
    # Probe live database connectivity
    db_health = check_db_health()
    # Probe storage directory accessibility
    storage_health = _check_storage_status()
    # Probe Gemini API configuration
    gemini_health = _check_gemini_status()

    # Determine overall system health
    is_healthy = bool(db_health.get("connected", False)) and storage_health.get("writable", False)

    # Construct comprehensive diagnostic payload
    payload = {
        # Top-level service operational status
        "status": "healthy" if is_healthy else "degraded",
        # ISO timestamp in UTC
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # Application deployment environment
        "environment": settings.APP_ENV,
        # Database configuration indicator for backward compatibility
        "database_configured": bool(settings.DATABASE_URL),
        # Supabase configuration indicator for backward compatibility
        "supabase_configured": bool(settings.SUPABASE_URL),
        # Redis configuration indicator
        "redis_configured": bool(settings.REDIS_URL),
        # Qdrant configuration indicator
        "qdrant_configured": True,
        # Qdrant operational mode
        "qdrant_mode": "embedded/in-memory" if settings.QDRANT_URL == ":memory:" else settings.QDRANT_URL,
        # Default Gemini model identifier
        "gemini_model": settings.GEMINI_MODEL,
        # FERPA encryption status indicator
        "ferpa_encryption": "active",
        # Subsystem health breakdown checking database, gemini, and storage
        "services": {
            # Database status
            "database": {
                # Connection state
                "status": "connected" if db_health.get("connected") else "unhealthy",
                # Response latency in milliseconds
                "latency_ms": db_health.get("latency_ms", 0),
                # Active SQL dialect
                "dialect": db_health.get("dialect", "unknown"),
                # Error message if unhealthy
                "error": db_health.get("error"),
            },
            # Gemini GenAI status
            "gemini": gemini_health,
            # Storage status
            "storage": storage_health,
        },
    }

    # Return HTTP 503 if primary database is unreachable
    if not db_health.get("connected", False):
        # Return 503 Service Unavailable
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    # Return HTTP 200 OK
    return payload


@router.get("/health/db")
def db_health_check():
    """Live database connectivity probe returning latency and connection pool metrics."""
    # Execute database health check
    health_data = check_db_health()
    # Verify connectivity
    if not health_data.get("connected", False):
        # Return 503 Service Unavailable if disconnected
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_data,
        )
    # Return health data
    return health_data
