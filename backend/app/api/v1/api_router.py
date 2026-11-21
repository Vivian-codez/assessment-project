# Module docstring explaining API v1 Router aggregator
"""Main API v1 Router aggregator."""

# Import APIRouter class from FastAPI framework
from fastapi import APIRouter

# Import authentication and user profile sub-router
from app.api.v1.auth import router as auth_router
# Import course management sub-router
from app.api.v1.courses import router as courses_router
# Import classroom and roster management sub-router
from app.api.v1.classrooms import router as classrooms_router
# Import assignment management sub-router
from app.api.v1.assignments import router as assignments_router
# Import matrix rubric management sub-router
from app.api.v1.rubrics import router as rubrics_router
# Import student submission handling sub-router
from app.api.v1.submissions import router as submissions_router
# Import AI evaluation and teacher grade stamping sub-router
from app.api.v1.grading import router as grading_router
# Import peer similarity analysis sub-router
from app.api.v1.similarity import router as similarity_router
# Import batch job status polling and background task sub-router
from app.api.v1.jobs import router as jobs_router
# Import course gradebook spreadsheet view sub-router
from app.api.v1.gradebook import router as gradebook_router
# Import course analytics and metrics report sub-router
from app.api.v1.reports import router as reports_router
# Import FERPA audit logging sub-router
from app.api.v1.audit import router as audit_router
# Import multi-tenant assignment folders and evaluation pipeline sub-router
from app.api.v1.folders import router as folders_router
# Import data deletion, trash bin, and privacy compliance sub-router
from app.api.v1.deletion import router as deletion_router

# Initialize master FastAPI v1 router instance
api_v1_router = APIRouter()

# Mount authentication router endpoints onto v1 router
api_v1_router.include_router(auth_router)
# Mount data deletion, 30-day trash bin, and privacy compliance endpoints first for priority matching
api_v1_router.include_router(deletion_router)
# Mount courses router endpoints onto v1 router
api_v1_router.include_router(courses_router)
# Mount classrooms router endpoints onto v1 router
api_v1_router.include_router(classrooms_router)
# Mount assignments router endpoints onto v1 router
api_v1_router.include_router(assignments_router)
# Mount rubrics router endpoints onto v1 router
api_v1_router.include_router(rubrics_router)
# Mount submissions router endpoints onto v1 router
api_v1_router.include_router(submissions_router)
# Mount grading router endpoints onto v1 router
api_v1_router.include_router(grading_router)
# Mount similarity router endpoints onto v1 router
api_v1_router.include_router(similarity_router)
# Mount batch jobs router endpoints onto v1 router
api_v1_router.include_router(jobs_router)
# Mount gradebook router endpoints onto v1 router
api_v1_router.include_router(gradebook_router)
# Mount reports router endpoints onto v1 router
api_v1_router.include_router(reports_router)
# Mount audit logs router endpoints onto v1 router
api_v1_router.include_router(audit_router)
# Mount multi-tenant assignment folders and evaluation endpoints onto v1 router
api_v1_router.include_router(folders_router)
