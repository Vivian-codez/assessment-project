"""Assignment API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.supabase import supabase
from app.core.logging import logger
from app.models.assignment import Assignment
from app.models.course import Course
from app.schemas.assignment import AssignmentCreate, AssignmentResponse

router = APIRouter(tags=["Assignments"])


@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentResponse])
def get_course_assignments(
    course_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all assignments for a specified course."""
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
    if not assignments:
        try:
            from app.core.supabase import supabase
            res = supabase.table("assignments").select("*").eq("course_id", course_id).execute()
            if res.data:
                for a_data in res.data:
                    if not db.query(Assignment).filter(Assignment.id == a_data["id"]).first():
                        db.add(Assignment(
                            id=a_data["id"],
                            course_id=a_data["course_id"],
                            title=a_data["title"],
                            description=a_data.get("description"),
                            max_score=float(a_data.get("max_score", 100.0)),
                            rubric_id=a_data.get("rubric_id"),
                            reference_assignment_text=a_data.get("reference_assignment_text"),
                        ))
                db.commit()
                assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
        except Exception as e:
            logger.warning(f"Supabase assignments sync notice: {e}")
    return assignments


def _ensure_course_in_supabase(course: Course):
    """Ensures parent course exists in Supabase so foreign key constraints pass."""
    try:
        c_res = supabase.table("courses").select("id").eq("id", course.id).execute()
        if not c_res.data:
            supabase.table("courses").insert({
                "id": course.id,
                "name": course.name,
                "code": course.code,
                "section": course.section or "A",
                "tone": getattr(course, "tone", "lav"),
                "students_count": getattr(course, "students_count", 0),
            }).execute()
            logger.info(f"Synchronized parent course {course.id} ({course.name}) to Supabase.")
    except Exception as e:
        logger.warning(f"Could not pre-sync course {course.id} to Supabase: {e}")


def _persist_assignment_record(
    course: Course,
    payload: AssignmentCreate,
    db: Session,
) -> Assignment:
    """Internal helper to create assignment in local DB and Supabase."""
    assign_id = f"assign_{uuid.uuid4().hex[:12]}"
    assignment = Assignment(
        id=assign_id,
        course_id=course.id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        max_score=payload.max_score,
        rubric_id=payload.rubric_id,
        reference_assignment_text=payload.reference_assignment_text,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # 1. Ensure parent course exists in Supabase to fulfill foreign key
    _ensure_course_in_supabase(course)

    # 2. Check if rubric_id exists in Supabase before attaching foreign key
    sb_rubric_id = None
    if assignment.rubric_id:
        try:
            r_check = supabase.table("rubrics").select("id").eq("id", assignment.rubric_id).execute()
            if r_check.data:
                sb_rubric_id = assignment.rubric_id
        except Exception:
            sb_rubric_id = None

    # 3. Upsert assignment into Supabase
    try:
        supabase.table("assignments").upsert({
            "id": assignment.id,
            "course_id": assignment.course_id,
            "title": assignment.title,
            "description": assignment.description,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "max_score": assignment.max_score,
            "rubric_id": sb_rubric_id,
            "reference_assignment_text": assignment.reference_assignment_text,
        }).execute()
        logger.info(f"Persisted assignment {assignment.id} to Supabase successfully.")
    except Exception as e:
        logger.warning(f"Supabase assignment sync notice for {assignment.id}: {e}")

    return assignment


@router.post("/courses/{course_id}/assignments", response_model=AssignmentResponse)
def create_course_assignment(
    course_id: str,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
):
    """Create a new assignment under a course with reference assignment support."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        # Check Supabase
        try:
            res = supabase.table("courses").select("*").eq("id", course_id).execute()
            if res.data:
                c_data = res.data[0]
                course = Course(
                    id=c_data["id"],
                    name=c_data["name"],
                    code=c_data["code"],
                    section=c_data.get("section", "A"),
                    tone=c_data.get("tone", "lav"),
                    students_count=c_data.get("students_count", 0),
                )
                db.add(course)
                db.commit()
                db.refresh(course)
        except Exception as e:
            logger.warning(f"Supabase course lookup error: {e}")

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return _persist_assignment_record(course=course, payload=payload, db=db)


@router.post("/assignments", response_model=AssignmentResponse)
def create_assignment_direct(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
):
    """Direct assignment creation endpoint (/api/v1/assignments).

    Accepts course_id in payload, defaulting to primary course if not provided.
    """
    course_id = payload.course_id
    course = None
    if course_id:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            try:
                res = supabase.table("courses").select("*").eq("id", course_id).execute()
                if res.data:
                    c_data = res.data[0]
                    course = Course(
                        id=c_data["id"],
                        name=c_data["name"],
                        code=c_data["code"],
                        section=c_data.get("section", "A"),
                        tone=c_data.get("tone", "lav"),
                        students_count=c_data.get("students_count", 0),
                    )
                    db.add(course)
                    db.commit()
            except Exception:
                pass

    if not course:
        # Pick first available course
        course = db.query(Course).first()
        if not course:
            course = Course(
                id=f"c_{uuid.uuid4().hex[:8]}",
                name="Data Structures",
                code="CS201",
                section="A",
                tone="lav",
            )
            db.add(course)
            db.commit()

    return _persist_assignment_record(course=course, payload=payload, db=db)


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment_detail(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve single assignment details."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        try:
            from app.core.supabase import supabase
            res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
            if res.data:
                a_data = res.data[0]
                assignment = Assignment(
                    id=a_data["id"],
                    course_id=a_data["course_id"],
                    title=a_data["title"],
                    description=a_data.get("description"),
                    max_score=float(a_data.get("max_score", 100.0)),
                    rubric_id=a_data.get("rubric_id"),
                    reference_assignment_text=a_data.get("reference_assignment_text"),
                )
                db.add(assignment)
                db.commit()
                db.refresh(assignment)
        except Exception as e:
            logger.warning(f"Supabase assignment detail sync notice: {e}")

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: str,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
):
    """Update assignment details, reference assignment text, or rubric."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    assignment.title = payload.title
    if payload.description is not None:
        assignment.description = payload.description
    if payload.due_date is not None:
        assignment.due_date = payload.due_date
    if payload.max_score is not None:
        assignment.max_score = payload.max_score
    if payload.rubric_id is not None:
        assignment.rubric_id = payload.rubric_id
    if payload.reference_assignment_text is not None:
        assignment.reference_assignment_text = payload.reference_assignment_text

    db.commit()
    db.refresh(assignment)

    try:
        supabase.table("assignments").update({
            "title": assignment.title,
            "description": assignment.description,
            "max_score": assignment.max_score,
            "rubric_id": assignment.rubric_id,
            "reference_assignment_text": assignment.reference_assignment_text,
        }).eq("id", assignment.id).execute()
    except Exception as e:
        logger.warning(f"Supabase assignment update notice: {e}")

    return assignment


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Delete an assignment and all its submissions and evaluations."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()

    try:
        supabase.table("assignments").delete().eq("id", assignment_id).execute()
    except Exception as e:
        logger.warning(f"Supabase assignment delete notice: {e}")

    return None

