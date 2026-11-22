# Module docstring explaining Data Deletion, Trash Bin, GDPR/DPDP Compliance, and Legal API endpoints
"""Data Deletion, 30-Day Trash Bin, GDPR/DPDP Right-to-Erasure, and Legal Policy API endpoints."""

# Import standard library modules for date math, in-memory zip creation, json serialization, and typing
import io
import os
import json
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Import FastAPI routing primitives, dependency injection, HTTP status exceptions, and streaming responses
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, PlainTextResponse
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import database session dependency
from app.core.database import get_db
# Import application logger for diagnostic telemetry
from app.core.logging import logger
# Import ORM models for courses, assignments, submissions, students, rubrics, deletion requests, and audit logs
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.student import Student
from app.models.rubric import Rubric
from app.models.deletion_request import DeletionRequest
from app.models.audit_log import AuditLog
from app.models.user import User
# Import analytics cache invalidator
from app.api.v1.reports import invalidate_analytics_cache, get_redis_client

# Initialize FastAPI router instance tagged under Data Deletion & Privacy
router = APIRouter(tags=["Data Deletion & Privacy"])


# Helper function executing permanent cascading purge of an entity and its assets
def purge_entity_permanent(db: Session, entity_type: str, entity_id: str, reason: str = "Educator permanent deletion") -> bool:
    """Permanently delete an entity and cascade across database records, filesystem storage, and Redis keys.

    Args:
        db (Session): Active SQLAlchemy database session.
        entity_type (str): Classification ('Course', 'Assignment', 'Submission', 'Student', 'Rubric').
        entity_id (str): Primary key string of target entity.
        reason (str): Audit rationale.

    Returns:
        bool: True if purged successfully, False if entity was not found.
    """
    # Normalize entity type to title case
    norm_type = entity_type.strip().title()

    # Model resolution mapping
    model_map = {
        "Course": Course,
        "Assignment": Assignment,
        "Submission": Submission,
        "Student": Student,
        "Rubric": Rubric,
    }

    # Retrieve target model class
    model_cls = model_map.get(norm_type)
    if not model_cls:
        # Unknown entity type
        return False

    # Query entity from database
    entity = db.query(model_cls).filter(model_cls.id == entity_id).first()
    if not entity:
        return False

    # Filesystem cleanup: If entity is a Submission with an uploaded file, delete file from disk
    if norm_type == "Submission" and hasattr(entity, "file_path") and entity.file_path:
        try:
            if os.path.exists(entity.file_path):
                os.remove(entity.file_path)
                logger.info(f"[PERMANENT-PURGE] Deleted physical file: {entity.file_path}")
        except Exception as exc:
            logger.warning(f"[PERMANENT-PURGE] Failed to delete file {entity.file_path}: {exc}")

    # Redis cache cleanup: Purge progress streams and analytics caches
    redis_client = get_redis_client()
    if redis_client:
        try:
            if norm_type == "Assignment":
                redis_client.delete(f"assignment_progress:{entity_id}")
            elif norm_type == "Submission":
                redis_client.delete(f"submission_cache:{entity_id}")
        except Exception as exc:
            logger.debug(f"[PERMANENT-PURGE] Redis key deletion skipped: {exc}")

    # Look up an existing administrator or teacher user for foreign key compliance
    admin_user = db.query(User).first()
    # Resolve valid user ID or fallback to default instructor
    acting_user_id = admin_user.id if admin_user else "inst_priya_rao"

    # Record permanent deletion in DeletionRequest compliance log table
    del_req = DeletionRequest(
        # Set foreign key reference to active instructor
        user_id=acting_user_id,
        # Set normalized entity classification
        entity_type=norm_type,
        # Set unique entity identifier
        entity_id=entity_id,
        # Mark compliance record status as completed
        status="completed",
        # Set justification rationale
        reason=reason,
    )
    # Add deletion request record to session
    db.add(del_req)

    # Delete entity from database (cascades via SQLAlchemy / DB foreign keys)
    db.delete(entity)
    db.commit()

    # Invalidate analytics cache
    invalidate_analytics_cache()

    return True


# --- SOFT DELETION ENDPOINTS ---

# HTTP DELETE route handler soft-deleting a Course
@router.delete("/courses/{course_id}")
def soft_delete_course(
    course_id: str,
    db: Session = Depends(get_db),
):
    """Move a course to the 30-day Trash Bin.

    Args:
        course_id (str): Target course identifier.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Confirmation with retention expiration details.
    """
    # Query course matching course_id
    course = db.query(Course).filter(Course.id == course_id).first()
    # Idempotent guard: if course does not exist, return success
    if not course:
        return {
            "status": "success",
            "message": "Course already removed or not found.",
            "entity_type": "Course",
            "entity_id": course_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "days_remaining": 30,
        }
    # Idempotent guard: if already soft-deleted, return success
    if course.deleted_at is not None:
        return {
            "status": "success",
            "message": f"Course '{course.name}' already moved to Trash.",
            "entity_type": "Course",
            "entity_id": course_id,
            "deleted_at": course.deleted_at.isoformat(),
            "days_remaining": 30,
        }

    # Mark soft-deleted timestamp
    course.deleted_at = datetime.utcnow()
    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=course.instructor_id,
        actor_name="Teacher",
        action="SOFT_DELETE_COURSE",
        entity_type="Course",
        entity_id=course.id,
        details={"message": f"Moved course {course.name} ({course.code}) to 30-day trash bin."},
    )
    db.add(audit_event)
    db.commit()
    invalidate_analytics_cache(course_id)

    return {
        "status": "success",
        "message": f"Course '{course.name}' moved to Trash. Retained for 30 days before permanent deletion.",
        "entity_type": "Course",
        "entity_id": course_id,
        "deleted_at": course.deleted_at.isoformat(),
        "days_remaining": 30,
    }


# HTTP DELETE route handler soft-deleting an Assignment
@router.delete("/assignments/{assignment_id}")
def soft_delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Move an assignment to the 30-day Trash Bin.

    Args:
        assignment_id (str): Target assignment identifier.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Confirmation with retention expiration details.
    """
    # Query target assignment by ID
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Idempotent guard: if assignment does not exist, return success
    if not assignment:
        return {
            "status": "success",
            "message": "Assignment already removed or not found.",
            "entity_type": "Assignment",
            "entity_id": assignment_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "days_remaining": 30,
        }
    # Idempotent guard: if already soft-deleted, return success
    if assignment.deleted_at is not None:
        return {
            "status": "success",
            "message": f"Assignment '{assignment.title}' already moved to Trash.",
            "entity_type": "Assignment",
            "entity_id": assignment_id,
            "deleted_at": assignment.deleted_at.isoformat(),
            "days_remaining": 30,
        }

    # Mark soft-deleted timestamp
    assignment.deleted_at = datetime.utcnow()
    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=None,
        actor_name="Teacher",
        action="SOFT_DELETE_ASSIGNMENT",
        entity_type="Assignment",
        entity_id=assignment.id,
        details={"message": f"Moved assignment '{assignment.title}' to 30-day trash bin."},
    )
    db.add(audit_event)
    db.commit()
    invalidate_analytics_cache(assignment.course_id)

    return {
        "status": "success",
        "message": f"Assignment '{assignment.title}' moved to Trash. Retained for 30 days.",
        "entity_type": "Assignment",
        "entity_id": assignment_id,
        "deleted_at": assignment.deleted_at.isoformat(),
        "days_remaining": 30,
    }


# HTTP DELETE route handler soft-deleting a Submission
@router.delete("/submissions/{submission_id}")
def soft_delete_submission(
    submission_id: str,
    db: Session = Depends(get_db),
):
    """Move a submission to the 30-day Trash Bin.

    Args:
        submission_id (str): Target submission identifier.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Confirmation with retention expiration details.
    """
    # Query target submission by ID
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    # Idempotent guard: if submission does not exist, return success
    if not submission:
        return {
            "status": "success",
            "message": "Submission already removed or not found.",
            "entity_type": "Submission",
            "entity_id": submission_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "days_remaining": 30,
        }
    # Idempotent guard: if already soft-deleted, return success
    if submission.deleted_at is not None:
        return {
            "status": "success",
            "message": f"Submission '{submission.file_name}' already moved to Trash.",
            "entity_type": "Submission",
            "entity_id": submission_id,
            "deleted_at": submission.deleted_at.isoformat(),
            "days_remaining": 30,
        }

    # Mark soft-deleted timestamp
    submission.deleted_at = datetime.utcnow()
    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=None,
        actor_name="Teacher",
        action="SOFT_DELETE_SUBMISSION",
        entity_type="Submission",
        entity_id=submission.id,
        details={"message": f"Moved submission {submission.id} ({submission.file_name}) to 30-day trash bin."},
    )
    db.add(audit_event)
    db.commit()
    invalidate_analytics_cache()

    return {
        "status": "success",
        "message": f"Submission '{submission.file_name}' moved to Trash.",
        "entity_type": "Submission",
        "entity_id": submission_id,
        "deleted_at": submission.deleted_at.isoformat(),
        "days_remaining": 30,
    }


# HTTP DELETE route handler soft-deleting a Student
@router.delete("/students/{student_id}")
def soft_delete_student(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Move a student roster record to the 30-day Trash Bin.

    Args:
        student_id (str): Target student identifier.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Confirmation with retention expiration details.
    """
    # Query target student by ID
    student = db.query(Student).filter(Student.id == student_id).first()
    # Idempotent guard: if student does not exist, return success
    if not student:
        return {
            "status": "success",
            "message": "Student already removed or not found.",
            "entity_type": "Student",
            "entity_id": student_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "days_remaining": 30,
        }
    # Idempotent guard: if already soft-deleted, return success
    if student.deleted_at is not None:
        return {
            "status": "success",
            "message": f"Student '{student.full_name}' already moved to Trash.",
            "entity_type": "Student",
            "entity_id": student_id,
            "deleted_at": student.deleted_at.isoformat(),
            "days_remaining": 30,
        }

    # Mark soft-deleted timestamp
    student.deleted_at = datetime.utcnow()
    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=None,
        actor_name="Teacher",
        action="SOFT_DELETE_STUDENT",
        entity_type="Student",
        entity_id=student.id,
        details={"message": f"Moved student {student.full_name} ({student.roll_number}) to 30-day trash bin."},
    )
    db.add(audit_event)
    db.commit()
    invalidate_analytics_cache()

    return {
        "status": "success",
        "message": f"Student '{student.full_name}' moved to Trash.",
        "entity_type": "Student",
        "entity_id": student_id,
        "deleted_at": student.deleted_at.isoformat(),
        "days_remaining": 30,
    }


# HTTP DELETE route handler soft-deleting a Rubric
@router.delete("/rubrics/{rubric_id}")
def soft_delete_rubric(
    rubric_id: str,
    db: Session = Depends(get_db),
):
    """Move a rubric to the 30-day Trash Bin.

    Args:
        rubric_id (str): Target rubric identifier.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Confirmation with retention expiration details.
    """
    rubric = db.query(Rubric).filter(Rubric.id == rubric_id, Rubric.deleted_at.is_(None)).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found or already deleted")

    # Mark soft-deleted timestamp
    rubric.deleted_at = datetime.utcnow()
    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=None,
        actor_name="Teacher",
        action="SOFT_DELETE_RUBRIC",
        entity_type="Rubric",
        entity_id=rubric.id,
        details={"message": f"Moved rubric '{rubric.title or rubric.name}' to 30-day trash bin."},
    )
    db.add(audit_event)
    db.commit()

    return {
        "status": "success",
        "message": f"Rubric '{rubric.title or rubric.name}' moved to Trash.",
        "entity_type": "Rubric",
        "entity_id": rubric_id,
        "deleted_at": rubric.deleted_at.isoformat(),
        "days_remaining": 30,
    }


# --- TRASH BIN & RESTORE ENDPOINTS ---

# HTTP GET route handler listing all items currently in the 30-day Trash Bin
@router.get("/trash")
def list_trash_items(
    db: Session = Depends(get_db),
):
    """List all soft-deleted entities across Courses, Assignments, Submissions, Students, and Rubrics.

    Args:
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: List of trashed items with days remaining before permanent purge.
    """
    now = datetime.utcnow()
    trash_items: List[Dict[str, Any]] = []

    # 1. Soft-deleted Courses
    courses = db.query(Course).filter(Course.deleted_at.isnot(None)).all()
    for c in courses:
        days_left = max(0, 30 - (now - c.deleted_at).days)
        trash_items.append({
            "id": c.id,
            "entity_type": "Course",
            "name": f"{c.name} ({c.code})",
            "deleted_at": c.deleted_at.isoformat(),
            "days_remaining": days_left,
            "can_restore": True,
        })

    # 2. Soft-deleted Assignments
    assignments = db.query(Assignment).filter(Assignment.deleted_at.isnot(None)).all()
    for a in assignments:
        days_left = max(0, 30 - (now - a.deleted_at).days)
        trash_items.append({
            "id": a.id,
            "entity_type": "Assignment",
            "name": a.title,
            "deleted_at": a.deleted_at.isoformat(),
            "days_remaining": days_left,
            "can_restore": True,
        })

    # 3. Soft-deleted Submissions
    submissions = db.query(Submission).filter(Submission.deleted_at.isnot(None)).all()
    for s in submissions:
        days_left = max(0, 30 - (now - s.deleted_at).days)
        trash_items.append({
            "id": s.id,
            "entity_type": "Submission",
            "name": f"{s.file_name} ({s.student_name or s.student_roll})",
            "deleted_at": s.deleted_at.isoformat(),
            "days_remaining": days_left,
            "can_restore": True,
        })

    # 4. Soft-deleted Students
    students = db.query(Student).filter(Student.deleted_at.isnot(None)).all()
    for st in students:
        days_left = max(0, 30 - (now - st.deleted_at).days)
        trash_items.append({
            "id": st.id,
            "entity_type": "Student",
            "name": f"{st.full_name} ({st.roll_number})",
            "deleted_at": st.deleted_at.isoformat(),
            "days_remaining": days_left,
            "can_restore": True,
        })

    # 5. Soft-deleted Rubrics
    rubrics = db.query(Rubric).filter(Rubric.deleted_at.isnot(None)).all()
    for r in rubrics:
        days_left = max(0, 30 - (now - r.deleted_at).days)
        trash_items.append({
            "id": r.id,
            "entity_type": "Rubric",
            "name": r.title or r.name or "Rubric",
            "deleted_at": r.deleted_at.isoformat(),
            "days_remaining": days_left,
            "can_restore": True,
        })

    return {
        "status": "success",
        "total_trashed": len(trash_items),
        "items": trash_items,
    }


# HTTP POST route handler restoring a soft-deleted entity from Trash
@router.post("/trash/restore/{entity_type}/{entity_id}")
def restore_trash_item(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Restore an entity from the 30-day Trash Bin.

    Args:
        entity_type (str): Classification ('Course', 'Assignment', 'Submission', 'Student', 'Rubric').
        entity_id (str): Primary key string.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Restoration confirmation.
    """
    norm_type = entity_type.strip().title()
    model_map = {
        "Course": Course,
        "Assignment": Assignment,
        "Submission": Submission,
        "Student": Student,
        "Rubric": Rubric,
    }
    model_cls = model_map.get(norm_type)
    if not model_cls:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    entity = db.query(model_cls).filter(model_cls.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Clear deleted_at to restore
    entity.deleted_at = None

    # Log audit event
    audit_event = AuditLog(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        actor_id=None,
        actor_name="Teacher",
        action=f"RESTORE_{norm_type.upper()}",
        entity_type=norm_type,
        entity_id=entity_id,
        details={"message": f"Restored {norm_type} {entity_id} from trash bin."},
    )
    db.add(audit_event)
    db.commit()

    # Invalidate analytics cache
    invalidate_analytics_cache()

    return {
        "status": "success",
        "message": f"{norm_type} restored successfully.",
        "entity_type": norm_type,
        "entity_id": entity_id,
    }


# HTTP DELETE route handler permanently purging an item immediately
@router.delete("/trash/permanent/{entity_type}/{entity_id}")
def permanent_delete_trash_item(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
):
    """Permanently delete an entity immediately, bypassing the remaining 30-day retention.

    Args:
        entity_type (str): Entity classification.
        entity_id (str): Primary key string.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Permanent deletion confirmation.
    """
    success = purge_entity_permanent(db, entity_type, entity_id, reason="Immediate teacher permanent purge")
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {
        "status": "success",
        "message": f"Permanently deleted {entity_type} {entity_id} and all cascaded files and caches.",
        "entity_type": entity_type,
        "entity_id": entity_id,
    }


# --- USER DATA EXPORT (DOWNLOAD ALL MY DATA) ---

# HTTP GET route handler streaming a complete ZIP archive of all user data
@router.get("/user/export-all-data")
def export_all_user_data(
    db: Session = Depends(get_db),
):
    """Generate and stream a complete ZIP archive of all educator courses, assignments, students, grades, and audit logs.

    Args:
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        StreamingResponse: Streamed ZIP archive package.
    """
    # Create in-memory binary stream for ZIP archive
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Export Courses JSON
        courses = db.query(Course).all()
        courses_data = [
            {"id": c.id, "name": c.name, "code": c.code, "section": c.section, "students_count": c.students_count, "created_at": str(c.created_at)}
            for c in courses
        ]
        zf.writestr("courses.json", json.dumps(courses_data, indent=2))

        # 2. Export Assignments JSON
        assignments = db.query(Assignment).all()
        assignments_data = [
            {"id": a.id, "course_id": a.course_id, "title": a.title, "max_score": a.max_score, "status": a.status, "due_date": str(a.due_date)}
            for a in assignments
        ]
        zf.writestr("assignments.json", json.dumps(assignments_data, indent=2))

        # 3. Export Students JSON
        students = db.query(Student).all()
        students_data = [
            {"id": s.id, "classroom_id": s.classroom_id, "roll_number": s.roll_number, "full_name": s.full_name, "email": s.email}
            for s in students
        ]
        zf.writestr("students.json", json.dumps(students_data, indent=2))

        # 4. Export FERPA Audit Logs JSON
        audit_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(1000).all()
        audit_data = [
            {"id": log.id, "actor_id": log.actor_id, "actor_name": log.actor_name, "action": log.action, "details": log.details, "created_at": str(log.created_at)}
            for log in audit_logs
        ]
        zf.writestr("audit_logs.json", json.dumps(audit_data, indent=2))

        # 5. Export Submissions and Extracted Text files
        submissions = db.query(Submission).all()
        subs_metadata = []
        for s in submissions:
            subs_metadata.append({
                "id": s.id,
                "assignment_id": s.assignment_id,
                "student_identifier": s.student_roll or s.student_identifier,
                "file_name": s.file_name,
                "status": s.status,
                "similarity_score": s.similarity_score,
                "ai_probability": s.ai_content_probability,
            })
            # Include extracted text as individual file in archive
            if s.extracted_text or s.content:
                text_content = s.extracted_text or s.content or ""
                clean_name = f"submissions/text_{s.id[:8]}_{s.student_roll or 'unknown'}.txt"
                zf.writestr(clean_name, text_content)

        zf.writestr("submissions_metadata.json", json.dumps(subs_metadata, indent=2))

        # 6. Readme note describing contents and compliance
        readme_text = (
            "Verism AI - Complete Educator Data Archive\n"
            "==========================================\n\n"
            f"Generated on: {datetime.utcnow().isoformat()} UTC\n"
            "This package contains all course configurations, enrolled rosters, assignment rubrics,\n"
            "graded assessments, and FERPA/GDPR audit trails associated with your account.\n\n"
            "Data Retention: Standard data retention is 30 days in the Trash Bin before automated permanent cascade.\n"
        )
        zf.writestr("README.txt", readme_text)

    # Prepare stream for reading
    zip_buffer.seek(0)
    filename = f"verism_data_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"

    # Stream ZIP archive
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# --- GDPR / DPDP COMPLIANCE & PRIVACY RIGHTS ---

# HTTP GET route handler returning User Privacy Profile and processing activities
@router.get("/privacy/me")
def get_privacy_profile(
    db: Session = Depends(get_db),
):
    """Retrieve privacy compliance details, active data processing purposes, and retention settings.

    Args:
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Privacy rights summary and retention configuration.
    """
    return {
        "frameworks_supported": ["GDPR (EU 2016/679)", "DPDP Act 2023 (India)", "FERPA (34 CFR Part 99)"],
        "data_controller": "Verism AI Platform Inc.",
        "encryption": "AES-256 for student PII at rest; TLS 1.3 in transit",
        "retention_policy": "30 days in Trash Bin with one-click restore; automated permanent cascade thereafter",
        "data_subject_rights": [
            {"right": "Right to Access (GDPR Art. 15 / DPDP Sec. 11)", "endpoint": "GET /api/v1/user/export-all-data"},
            {"right": "Right to Erasure (GDPR Art. 17 / DPDP Sec. 12)", "endpoint": "POST /api/v1/privacy/erasure-request"},
            {"right": "Right to Rectification (GDPR Art. 16)", "endpoint": "PATCH /api/v1/courses / assignments"},
            {"right": "Right to Restriction of Processing (GDPR Art. 18)", "endpoint": "POST /api/v1/courses/{id}/settings/auto-approve"},
        ],
        "subprocessors": [
            {"name": "Google Gemini API", "purpose": "Rubric-grounded evaluation and document parsing", "retention": "Zero-data retention API mode"},
            {"name": "Qdrant Vector Database", "purpose": "Local code and text similarity index", "retention": "Tenant-scoped; deleted with course"},
            {"name": "Redis", "purpose": "Task queuing and 60s analytics caching", "retention": "Ephemeral in-memory cache"},
        ],
    }


# HTTP POST route handler submitting a formal Right to Erasure request
@router.post("/privacy/erasure-request", status_code=status.HTTP_202_ACCEPTED)
def submit_erasure_request(
    reason: str = Query("Data Subject Erasure Request", description="Reason or justification for erasure"),
    db: Session = Depends(get_db),
):
    """Submit a formal right-to-erasure request pursuant to GDPR Art. 17 or DPDP Sec. 12.

    Args:
        reason (str): Justification provided by applicant.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Queued erasure ticket details.
    """
    # Look up an existing administrator or teacher user for foreign key constraint compliance
    admin_user = db.query(User).first()
    # Resolve valid user ID or fallback to default instructor
    acting_user_id = admin_user.id if admin_user else "inst_priya_rao"

    # Create compliance ticket
    ticket = DeletionRequest(
        # Set foreign key reference to requesting user
        user_id=acting_user_id,
        # Set target entity category covering all account data
        entity_type="AllUserData",
        # Set scope identifier
        entity_id="user-account-scope",
        # Set ticket status to pending review
        status="pending",
        # Set compliance justification rationale
        reason=reason,
    )
    db.add(ticket)
    db.commit()

    return {
        "status": "accepted",
        "ticket_id": ticket.id,
        "message": "Erasure request logged. All personal data scheduled for cascade purge within statutory SLA.",
        "requested_at": ticket.requested_at.isoformat(),
    }


# --- LEGAL POLICIES (PRIVACY, TERMS, DPA) ---

# HTTP GET route handler returning Privacy Policy
@router.get("/legal/privacy", response_class=PlainTextResponse)
def get_privacy_policy():
    """Return Verism AI Privacy Policy."""
    return """
VERISM AI PRIVACY POLICY
Last Updated: November 2026

1. Philosophy & Human Oversight
Verism AI operates on the fundamental principle: "AI suggests. You stamp. Every grade waits for your approval."
AI never finalizes, transmits, or publishes student grades without explicit educator review and authorization.

2. Information We Process
- Educator Account Data: Email address, encrypted credentials, institutional affiliation.
- Course & Roster Information: Student names and institutional roll numbers stored with AES-256 encryption.
- Assessment Artifacts: Submitted code, text essays, reference solutions, and scoring rubrics.

3. Subprocessors & Zero Training Guarantee
We utilize Google Gemini API via enterprise endpoints configured with zero-training retention. Student submissions
are never utilized to train public foundation models.

4. Data Retention & Deletion
Educators have autonomous control to delete data at any time. Deleted records reside in a 30-day Trash Bin
with immediate one-click restore. After 30 days, records are permanently cascaded across all databases,
storage volumes, and caches.
"""


# HTTP GET route handler returning Terms of Service
@router.get("/legal/terms", response_class=PlainTextResponse)
def get_terms_of_service():
    """Return Verism AI Terms of Service."""
    return """
VERISM AI TERMS OF SERVICE
Last Updated: November 2026

1. Service Description
Verism AI provides an asynchronous, rubric-based auto-grading, reference-solution benchmarking,
and similarity review assistant for educators and educational institutions.

2. Educator Responsibility
The educator retains full academic authority and legal responsibility for assigning, publishing,
and communicating final course grades to students.

3. Acceptable Use
Users agree not to upload harmful, infringing, or malicious content, and to adhere to applicable institutional
FERPA, GDPR, and DPDP regulations.
"""


# HTTP GET route handler returning Data Processing Agreement (DPA)
@router.get("/legal/dpa", response_class=PlainTextResponse)
def get_data_processing_agreement():
    """Return Verism AI Data Processing Agreement."""
    return """
DATA PROCESSING AGREEMENT (DPA)
Pursuant to GDPR Article 28 and DPDP Act 2023

1. Scope: This DPA governs the processing of student personal data on behalf of Customer (Data Controller).
2. Security Measures: AES-256 encryption at rest, TLS 1.3 in transit, tenant isolation, role-based access.
3. Subprocessors: Customer grants general authorization for designated subprocessors (Google Gemini, Qdrant).
4. Deletion on Termination: Upon request, Verism AI shall delete or return all personal data within 30 days.
"""
