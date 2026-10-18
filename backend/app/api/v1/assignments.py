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
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


@router.post("/courses/{course_id}/assignments", response_model=AssignmentResponse)
def create_assignment(
    course_id: str,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
):
    """Create a new assignment under a course with reference assignment support."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assign_id = f"a_{uuid.uuid4().hex[:8]}"
    assignment = Assignment(
        id=assign_id,
        course_id=course_id,
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

    # Sync to Supabase
    try:
        supabase.table("assignments").upsert({
            "id": assignment.id,
            "course_id": assignment.course_id,
            "title": assignment.title,
            "description": assignment.description,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "max_score": assignment.max_score,
            "rubric_id": assignment.rubric_id,
            "reference_assignment_text": assignment.reference_assignment_text,
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase assignment sync notice: {e}")

    return assignment


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment_detail(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve single assignment details."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
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

