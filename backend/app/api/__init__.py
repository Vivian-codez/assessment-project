# Module docstring explaining API Routers package
"""API Routers package."""

# Import submissions router alias
from app.api.submissions import router as submissions_router
# Import grading router alias
from app.api.grading import router as grading_router
# Import rubrics router alias
from app.api.rubrics import router as rubrics_router
# Import jobs router alias
from app.api.jobs import router as jobs_router
# Import health check router
from app.api.health import router as health_router

# Export all aggregated router symbols
__all__ = [
    # Export submissions router
    "submissions_router",
    # Export grading router
    "grading_router",
    # Export rubrics router
    "rubrics_router",
    # Export jobs router
    "jobs_router",
    # Export health check router
    "health_router",
]
