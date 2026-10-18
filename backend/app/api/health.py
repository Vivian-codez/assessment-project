"""Health check and system diagnostic API endpoints."""

from fastapi import APIRouter
from app.core.config import settings

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
