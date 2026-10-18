"""API Routers package."""

from app.api.submissions import router as submissions_router
from app.api.grading import router as grading_router
from app.api.rubrics import router as rubrics_router
from app.api.jobs import router as jobs_router
from app.api.health import router as health_router

__all__ = [
    "submissions_router",
    "grading_router",
    "rubrics_router",
    "jobs_router",
    "health_router",
]
