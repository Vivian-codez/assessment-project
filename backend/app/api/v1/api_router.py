"""Main API v1 Router aggregator."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.rubrics import router as rubrics_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.grading import router as grading_router
from app.api.v1.similarity import router as similarity_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.gradebook import router as gradebook_router
from app.api.v1.reports import router as reports_router
from app.api.v1.audit import router as audit_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(courses_router)
api_v1_router.include_router(assignments_router)
api_v1_router.include_router(rubrics_router)
api_v1_router.include_router(submissions_router)
api_v1_router.include_router(grading_router)
api_v1_router.include_router(similarity_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(gradebook_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(audit_router)
