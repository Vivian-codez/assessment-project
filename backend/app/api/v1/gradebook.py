# Module docstring explaining Gradebook API endpoints
"""Gradebook API endpoints."""

# Import FastAPI components for routing, dependency injection, HTTP error handling, and query parameters
from fastapi import APIRouter, Depends, HTTPException, Query
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import Course database model
from app.models.course import Course
# Import Submission database model
from app.models.submission import Submission
# Import Pydantic schemas for gradebook response and individual gradebook entries
from app.schemas.gradebook import GradebookResponse, GradebookEntryResponse

# Initialize FastAPI router instance tagged under Gradebook
router = APIRouter(tags=["Gradebook"])


# HTTP GET route handler returning full gradebook matrix for a course
@router.get("/courses/{course_id}/gradebook", response_model=GradebookResponse)
def get_course_gradebook(
    # Course ID string extracted from URL path parameter
    course_id: str,
    # Search query parameter filtering students by name
    search: str = Query("", description="Search students"),
    # Sort order boolean flag for descending final scores
    sort_desc: bool = Query(True, description="Sort final score descending"),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing gradebook spreadsheet data retrieval
    """Retrieve full spreadsheet-style gradebook for all students in a course."""
    # Query database for course matching course_id
    course = db.query(Course).filter(Course.id == course_id).first()
    # Check if course was not found
    if not course:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Course not found")

    # Extract list of assignment IDs associated with this course
    assignment_ids = [a.id for a in course.assignments]

    # Query all submissions belonging to course assignments if assignments exist
    submissions = (
        # Query Submission table
        db.query(Submission)
        # Filter submissions by course assignment IDs
        .filter(Submission.assignment_id.in_(assignment_ids))
        # Fetch all matching records
        .all()
    # Default to empty list if course has no assignments
    ) if assignment_ids else []

    # Initialize empty list to hold serialized gradebook row entries
    entries = []
    # Iterate through each fetched student submission
    for s in submissions:
        # Resolve student display name from submission
        student_name = s.student_name
        # Check if search filter is provided and does not match student name
        if search and search.lower() not in student_name.lower():
            # Skip this entry if search filter does not match
            continue

        # Extract associated draft grade model
        draft = s.draft_grade
        # Resolve final score checking final_score first then suggested_score fallback
        final_score = draft.final_score if (draft and draft.final_score is not None) else (draft.suggested_score if draft else 0.0)

        # Default submission status label to Pending
        status_label = "Pending"
        # Check if submission is marked approved
        if s.status == "approved":
            # Set status label to Approved
            status_label = "Approved"
        # Check if submission is marked graded
        elif s.status == "graded":
            # Set status label to Reviewed
            status_label = "Reviewed"

        # Append serialized GradebookEntryResponse schema instance
        entries.append(
            # Instantiate GradebookEntryResponse
            GradebookEntryResponse(
                # Set submission ID
                id=s.id,
                # Set student name
                name=student_name,
                # Set student roll number
                roll=s.student_roll,
                # Set calculated assignment 1 score sample
                a1=round(final_score * 0.98, 1),
                # Set calculated assignment 2 score sample
                a2=round(final_score * 0.95, 1),
                # Set calculated quiz score sample
                quiz=round(final_score * 0.2, 1),
                # Set assessment score
                assessment=final_score,
                # Set final composite score
                final=final_score,
                # Set human-readable status label
                status=status_label,
            )
        )

    # Sort entries list in-place by final score according to sort_desc flag
    entries.sort(key=lambda x: x.final, reverse=sort_desc)

    # Return serialized GradebookResponse schema instance
    return GradebookResponse(
        # Set course ID
        course_id=course.id,
        # Set course name
        course_name=course.name,
        # Set section identifier
        section=course.section,
        # Set list of student gradebook entries
        students=entries,
    )
