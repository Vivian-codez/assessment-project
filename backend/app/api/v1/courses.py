"""Course Management API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.schemas.course import CourseCreate, CourseResponse, CourseDetailResponse
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor
from app.core.logging import logger

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=List[CourseResponse])
def get_courses(
    search: str = Query("", description="Search by name, code, or section"),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all courses for the instructor dashboard."""
    # 1. If cloud Supabase is enabled, optionally sync courses
    if settings.USE_SUPABASE:
        try:
            from app.core.supabase import supabase
            sb_res = supabase.table("courses").select("*").execute()
            for s_data in (sb_res.data or []):
                s_id = str(s_data["id"])
                existing = db.query(Course).filter(Course.id == s_id).first()
                if not existing:
                    db.add(Course(
                        id=s_id,
                        name=s_data["name"],
                        code=s_data["code"],
                        section=s_data.get("section", "A"),
                        tone=s_data.get("tone", "lav"),
                        students_count=s_data.get("students_count", 0),
                        instructor_id=s_data.get("instructor_id"),
                    ))
            db.commit()
        except Exception as e:
            logger.debug(f"Cloud courses sync notice: {e}")

    # 2. Query courses from local database
    query = db.query(Course)
    if instructor and instructor.id:
        inst_courses = query.filter((Course.instructor_id == instructor.id) | (Course.instructor_id == None)).all()
        courses = inst_courses if inst_courses else query.all()
    else:
        courses = query.all()

    if search:
        search_lower = search.lower()
        courses = [
            c for c in courses
            if search_lower in (c.name or "").lower()
            or search_lower in (c.code or "").lower()
            or search_lower in (c.section or "").lower()
        ]

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

        # Get live student count from Student table if enrolled
        live_students = db.query(Student).filter(Student.classroom_id == c.id).count()
        student_count = live_students if live_students > 0 else (c.students_count or 0)

        results.append(
            CourseResponse(
                id=c.id,
                name=c.name,
                code=c.code,
                section=c.section,
                tone=c.tone,
                students=student_count,
                students_count=student_count,
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
    instructor: Instructor = Depends(get_current_instructor),
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

    live_students = db.query(Student).filter(Student.classroom_id == course.id).count()
    student_count = live_students if live_students > 0 else (course.students_count or 0)

    return CourseDetailResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        section=course.section,
        tone=course.tone,
        students=student_count,
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
    course_id = str(uuid.uuid4())
    inst_id = instructor.id if instructor else None
    new_course = Course(
        id=course_id,
        name=payload.name,
        code=payload.code,
        section=payload.section,
        tone=payload.tone,
        students_count=payload.students_count,
        instructor_id=inst_id,
    )
    db.add(new_course)

    # Ensure matching Classroom row exists
    new_classroom = Classroom(
        id=course_id,
        name=payload.name,
        code=payload.code,
        instructor_id=inst_id,
    )
    db.add(new_classroom)
    db.commit()
    db.refresh(new_course)

    if settings.USE_SUPABASE:
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
            supabase.table("classrooms").upsert({
                "id": new_course.id,
                "name": new_course.name,
                "code": new_course.code,
                "instructor_id": new_course.instructor_id,
            }).execute()
        except Exception as e:
            logger.warning(f"Cloud course/classroom sync notice: {e}")

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

    # Also delete corresponding classroom if exists
    cl = db.query(Classroom).filter(Classroom.id == course_id).first()
    if cl:
        db.delete(cl)

    db.delete(course)
    db.commit()

    if settings.USE_SUPABASE:
        try:
            from app.core.supabase import supabase
            supabase.table("courses").delete().eq("id", course_id).execute()
            supabase.table("classrooms").delete().eq("id", course_id).execute()
        except Exception as e:
            logger.warning(f"Cloud course delete notice: {e}")

    return None


@router.get("/{course_id}/rubrics")
def get_course_rubrics_alias(
    course_id: str,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all rubrics for a given course (alias for /rubrics/courses/{course_id}/rubrics)."""
    from app.api.v1.rubrics import list_rubrics
    return list_rubrics(classroom_id=course_id, course_id=course_id, db=db, current_instructor=instructor)
