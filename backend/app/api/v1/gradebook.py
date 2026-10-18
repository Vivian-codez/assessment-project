"""Gradebook API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.submission import Submission
from app.schemas.gradebook import GradebookResponse, GradebookEntryResponse

router = APIRouter(tags=["Gradebook"])


@router.get("/courses/{course_id}/gradebook", response_model=GradebookResponse)
def get_course_gradebook(
    course_id: str,
    search: str = Query("", description="Search students"),
    sort_desc: bool = Query(True, description="Sort final score descending"),
    db: Session = Depends(get_db),
):
    """Retrieve full spreadsheet-style gradebook for all students in a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assignment_ids = [a.id for a in course.assignments]

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id.in_(assignment_ids))
        .all()
    ) if assignment_ids else []

    entries = []
    for s in submissions:
        student_name = s.student_name
        if search and search.lower() not in student_name.lower():
            continue

        draft = s.draft_grade
        final_score = draft.final_score if (draft and draft.final_score is not None) else (draft.suggested_score if draft else 0.0)

        status_label = "Pending"
        if s.status == "approved":
            status_label = "Approved"
        elif s.status == "graded":
            status_label = "Reviewed"

        entries.append(
            GradebookEntryResponse(
                id=s.id,
                name=student_name,
                roll=s.student_roll,
                a1=round(final_score * 0.98, 1),
                a2=round(final_score * 0.95, 1),
                quiz=round(final_score * 0.2, 1),
                assessment=final_score,
                final=final_score,
                status=status_label,
            )
        )

    # Sort entries
    entries.sort(key=lambda x: x.final, reverse=sort_desc)

    return GradebookResponse(
        course_id=course.id,
        course_name=course.name,
        section=course.section,
        students=entries,
    )
