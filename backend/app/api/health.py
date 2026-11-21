"""Health check and system diagnostic API endpoints."""

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import check_db_health, get_db_pool_status

# Initialize FastAPI router instance tagged under Health
router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """System health check and diagnostic probe."""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "database_configured": bool(settings.DATABASE_URL),
        "supabase_configured": bool(settings.SUPABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
        "qdrant_configured": True,
        "qdrant_mode": "embedded/in-memory" if settings.QDRANT_URL == ":memory:" else settings.QDRANT_URL,
        "gemini_model": settings.GEMINI_MODEL,
        "ferpa_encryption": "active",
    }


@router.get("/health/db")
def db_health_check():
    """Live database connectivity probe returning latency and connection pool metrics."""
    health_data = check_db_health()
    if not health_data.get("connected", False):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_data,
        )
    return health_data
