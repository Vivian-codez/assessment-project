"""Course Management API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.schemas.course import CourseCreate, CourseResponse, CourseDetailResponse
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=List[CourseResponse])
def get_courses(
    search: str = Query("", description="Search by name, code, or section"),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all courses with aggregated metrics for the instructor dashboard."""
    query = db.query(Course).filter(Course.instructor_id == instructor.id)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Course.name.ilike(search_pattern)) |
            (Course.code.ilike(search_pattern)) |
            (Course.section.ilike(search_pattern))
        )
    courses = query.all()
    if not courses and not search:
        # Fallback to Supabase courses
        try:
            from app.core.supabase import supabase
            res = supabase.table("courses").select("*").execute()
            if res.data:
                for c_data in res.data:
                    if not db.query(Course).filter(Course.id == c_data["id"]).first():
                        db.add(Course(
                            id=c_data["id"],
                            name=c_data["name"],
                            code=c_data["code"],
                            section=c_data.get("section", "A"),
                            tone=c_data.get("tone", "lav"),
                            students_count=c_data.get("students_count", 0),
                            instructor_id=c_data.get("instructor_id"),
                        ))
                db.commit()
                courses = query.all() or db.query(Course).all()
        except Exception as e:
            logger.warning(f"Supabase courses sync notice: {e}")

    if not courses and not search:
        # Fallback to seeded demo courses for prototype display
        courses = db.query(Course).all()

    results = []
    for c in courses:
        # Calculate real-time counts
        assignment_ids = [a.id for a in c.assignments]
        assign_count = len(assignment_ids)

        pending_reviews = 0
        similarity_flags = 0

        if assignment_ids:
            pending_reviews = (
                db.query(DraftGrade)
                .join(Submission, DraftGrade.submission_id == Submission.id)
                .filter(Submission.assignment_id.in_(assignment_ids))
                .filter(DraftGrade.status != "approved")
                .count()
            )
            similarity_flags = (
                db.query(SimilarityMatch)
                .filter(SimilarityMatch.assignment_id.in_(assignment_ids))
                .filter(SimilarityMatch.status == "High similarity")
                .count()
            )

        results.append(
            CourseResponse(
                id=c.id,
                name=c.name,
                code=c.code,
                section=c.section,
                tone=c.tone,
                students=c.students_count,
                students_count=c.students_count,
                assignments=assign_count,
                assignments_count=assign_count,
                reviews=pending_reviews,
                reviews_count=pending_reviews,
                flags=similarity_flags,
                flags_count=similarity_flags,
            )
        )
    return results


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course_detail(
    course_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve detailed metadata and health metrics for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assignment_ids = [a.id for a in course.assignments]
    pending_reviews = (
        db.query(DraftGrade)
        .join(Submission, DraftGrade.submission_id == Submission.id)
        .filter(Submission.assignment_id.in_(assignment_ids))
        .filter(DraftGrade.status != "approved")
        .count()
    ) if assignment_ids else 0

    return CourseDetailResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        section=course.section,
        tone=course.tone,
        students=course.students_count,
        assignments=len(course.assignments),
        reviews=pending_reviews,
        flags=0,
        health="On track",
        next_deadline="18 October 2024",
        average_score=78.0,
    )


@router.post("", response_model=CourseResponse)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Add a new course."""
    new_course = Course(
        id=f"c_{uuid.uuid4().hex[:8]}",
        name=payload.name,
        code=payload.code,
        section=payload.section,
        tone=payload.tone,
        students_count=payload.students_count,
        instructor_id=instructor.id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    try:
        from app.core.supabase import supabase
        supabase.table("courses").upsert({
            "id": new_course.id,
            "name": new_course.name,
            "code": new_course.code,
            "section": new_course.section,
            "tone": new_course.tone,
            "students_count": new_course.students_count,
            "instructor_id": new_course.instructor_id,
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase course sync notice: {e}")

    return CourseResponse(
        id=new_course.id,
        name=new_course.name,
        code=new_course.code,
        section=new_course.section,
        tone=new_course.tone,
        students=new_course.students_count,
        assignments=0,
        reviews=0,
        flags=0,
    )


@router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Delete a course and all associated assignments and submissions."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()

    try:
        from app.core.supabase import supabase
        supabase.table("courses").delete().eq("id", course_id).execute()
    except Exception as e:
        logger.warning(f"Supabase course delete notice: {e}")

    return None

