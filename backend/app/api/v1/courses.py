# Module docstring explaining course management API endpoints
"""Course Management API endpoints."""

# Import uuid module to generate unique identifiers for new courses
import uuid
# Import List generic type annotation from typing module for response serialization
from typing import List
# Import FastAPI components for routing, dependencies, HTTP error responses, and query parameters
from fastapi import APIRouter, Depends, HTTPException, Query
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import application settings singleton containing configuration constants
from app.core.config import settings
# Import database session generator dependency
from app.core.database import get_db
# Import Course database model
from app.models.course import Course
# Import Classroom database model
from app.models.classroom import Classroom
# Import Student database model
from app.models.student import Student
# Import Assignment database model
from app.models.assignment import Assignment
# Import Submission database model
from app.models.submission import Submission
# Import DraftGrade database model
from app.models.draft_grade import DraftGrade
# Import SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch
# Import Pydantic schemas for course creation, summary response, and detailed response
from app.schemas.course import CourseCreate, CourseResponse, CourseDetailResponse
# Import authentication dependency resolving the current instructor
from app.api.v1.auth import get_current_instructor
# Import Instructor database model
from app.models.instructor import Instructor
# Import application logger for debugging and operational notices
from app.core.logging import logger

# Initialize FastAPI router instance with /courses prefix and Courses tag
router = APIRouter(prefix="/courses", tags=["Courses"])


# HTTP GET route handler returning list of courses with calculated metrics
@router.get("", response_model=List[CourseResponse])
def get_courses(
    # Search query parameter filtering by course name, code, or section
    search: str = Query("", description="Search by name, code, or section"),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing course list retrieval
    """Retrieve all courses for the instructor dashboard."""
    # 1. If cloud Supabase is enabled, optionally sync courses
    if settings.USE_SUPABASE:
        # Wrap Supabase synchronization in try-except block
        try:
            # Import Supabase client singleton dynamically
            from app.core.supabase import supabase
            # Query all course rows from Supabase courses table
            sb_res = supabase.table("courses").select("*").execute()
            # Iterate through each fetched course row
            for s_data in (sb_res.data or []):
                # Convert ID to string
                s_id = str(s_data["id"])
                # Query local database to check if course already exists
                existing = db.query(Course).filter(Course.id == s_id).first()
                # Check if course is missing from local database
                if not existing:
                    # Add newly discovered course to local database session
                    db.add(Course(
                        # Set course identifier
                        id=s_id,
                        # Set course name
                        name=s_data["name"],
                        # Set course catalog code
                        code=s_data["code"],
                        # Set course section defaulting to A
                        section=s_data.get("section", "A"),
                        # Set UI color tone defaulting to lav
                        tone=s_data.get("tone", "lav"),
                        # Set student enrollment count
                        students_count=s_data.get("students_count", 0),
                        # Set foreign key to instructor
                        instructor_id=s_data.get("instructor_id"),
                    ))
            # Commit synchronized course entities to database
            db.commit()
        # Catch network or synchronization errors
        except Exception as e:
            # Log debug notification regarding sync failure
            logger.debug(f"Cloud courses sync notice: {e}")

    # 2. Query courses from local database
    # Construct base query targeting Course database model
    query = db.query(Course)
    # Check if authenticated instructor has a valid ID
    if instructor and instructor.id:
        # Filter courses owned by instructor or unassigned courses
        inst_courses = query.filter((Course.instructor_id == instructor.id) | (Course.instructor_id == None)).all()
        # Use instructor filtered courses if any exist, otherwise return all courses
        courses = inst_courses if inst_courses else query.all()
    # Handle unassigned or anonymous instructor contexts
    else:
        # Return all courses from database
        courses = query.all()

    # Check if a non-empty search query string was provided
    if search:
        # Convert search query to lowercase for case-insensitive matching
        search_lower = search.lower()
        # Filter courses whose name, code, or section contain search query
        courses = [
            # Retain matching course
            c for c in courses
            # Match search against lowercase name
            if search_lower in (c.name or "").lower()
            # Match search against lowercase code
            or search_lower in (c.code or "").lower()
            # Match search against lowercase section
            or search_lower in (c.section or "").lower()
        ]

    # Initialize list to hold serialized course response models
    results = []
    # Iterate over each resolved course entity
    for c in courses:
        # Calculate real-time counts
        # Extract list of assignment IDs associated with this course
        assignment_ids = [a.id for a in c.assignments]
        # Count total assignments configured for course
        assign_count = len(assignment_ids)

        # Initialize pending reviews counter to zero
        pending_reviews = 0
        # Initialize similarity flags counter to zero
        similarity_flags = 0

        # Check if course has any assignments
        if assignment_ids:
            # Query count of draft grades that are not yet approved
            pending_reviews = (
                # Query DraftGrade table
                db.query(DraftGrade)
                # Join Submission on submission foreign key
                .join(Submission, DraftGrade.submission_id == Submission.id)
                # Filter submissions belonging to course assignments
                .filter(Submission.assignment_id.in_(assignment_ids))
                # Filter grades not marked as approved
                .filter(DraftGrade.status != "approved")
                # Count total matching records
                .count()
            )
            # Query count of similarity matches flagged as high similarity
            similarity_flags = (
                # Query SimilarityMatch table
                db.query(SimilarityMatch)
                # Filter matches belonging to course assignments
                .filter(SimilarityMatch.assignment_id.in_(assignment_ids))
                # Filter matches marked as High similarity
                .filter(SimilarityMatch.status == "High similarity")
                # Count total matching records
                .count()
            )

        # Get live student count from Student table if enrolled
        # Count enrolled student records matching course ID as classroom ID
        live_students = db.query(Student).filter(Student.classroom_id == c.id).count()
        # Use live count if greater than zero, otherwise fallback to cached count
        student_count = live_students if live_students > 0 else (c.students_count or 0)

        # Append formatted CourseResponse model to results list
        results.append(
            # Instantiate CourseResponse schema
            CourseResponse(
                # Set course ID
                id=c.id,
                # Set course name
                name=c.name,
                # Set course catalog code
                code=c.code,
                # Set section identifier
                section=c.section,
                # Set UI color theme tone
                tone=c.tone,
                # Set legacy students count attribute
                students=student_count,
                # Set modern students count attribute
                students_count=student_count,
                # Set legacy assignments count attribute
                assignments=assign_count,
                # Set modern assignments count attribute
                assignments_count=assign_count,
                # Set legacy reviews count attribute
                reviews=pending_reviews,
                # Set modern reviews count attribute
                reviews_count=pending_reviews,
                # Set legacy flags count attribute
                flags=similarity_flags,
                # Set modern flags count attribute
                flags_count=similarity_flags,
            )
        )
    # Return complete list of serialized course responses
    return results


# HTTP GET route handler returning detailed metrics for a specific course
@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course_detail(
    # Course ID string extracted from path parameter
    course_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing course detail retrieval
    """Retrieve detailed metadata and health metrics for a course."""
    # Query database for course matching course_id
    course = db.query(Course).filter(Course.id == course_id).first()
    # Check if course was not found
    if not course:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Course not found")

    # Extract assignment IDs belonging to course
    assignment_ids = [a.id for a in course.assignments]
    # Calculate pending review count if assignments exist, otherwise zero
    pending_reviews = (
        # Query DraftGrade table
        db.query(DraftGrade)
        # Join Submission on foreign key
        .join(Submission, DraftGrade.submission_id == Submission.id)
        # Filter submissions belonging to course assignments
        .filter(Submission.assignment_id.in_(assignment_ids))
        # Filter grades not approved
        .filter(DraftGrade.status != "approved")
        # Count total records
        .count()
    ) if assignment_ids else 0

    # Query live count of enrolled students in classroom
    live_students = db.query(Student).filter(Student.classroom_id == course.id).count()
    # Use live count if positive, otherwise fallback to cached students_count
    student_count = live_students if live_students > 0 else (course.students_count or 0)

    # Return serialized CourseDetailResponse schema
    return CourseDetailResponse(
        # Set course ID
        id=course.id,
        # Set course name
        name=course.name,
        # Set course code
        code=course.code,
        # Set course section
        section=course.section,
        # Set UI color tone
        tone=course.tone,
        # Set student count
        students=student_count,
        # Set total assignment count
        assignments=len(course.assignments),
        # Set pending reviews count
        reviews=pending_reviews,
        # Set similarity flags count to zero default
        flags=0,
        # Set health metric status indicator
        health="On track",
        # Set next deadline date string
        next_deadline="18 October 2024",
        # Set average class score float
        average_score=78.0,
    )


# HTTP POST route handler creating a new course entity
@router.post("", response_model=CourseResponse)
def create_course(
    # Validate incoming JSON creation payload using CourseCreate schema
    payload: CourseCreate,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing course creation
    """Add a new course."""
    # Generate unique UUID string for new course
    course_id = str(uuid.uuid4())
    # Extract instructor ID if instructor is present
    inst_id = instructor.id if instructor else None
    # Instantiate new Course database model
    new_course = Course(
        # Set course ID
        id=course_id,
        # Set course name from payload
        name=payload.name,
        # Set course code from payload
        code=payload.code,
        # Set section from payload
        section=payload.section,
        # Set UI color tone from payload
        tone=payload.tone,
        # Set student enrollment count from payload
        students_count=payload.students_count,
        # Set instructor foreign key
        instructor_id=inst_id,
    )
    # Stage new course entity in database session
    db.add(new_course)

    # Ensure matching Classroom row exists
    # Instantiate corresponding Classroom entity with identical ID
    new_classroom = Classroom(
        # Set classroom ID matching course ID
        id=course_id,
        # Set classroom name
        name=payload.name,
        # Set classroom code
        code=payload.code,
        # Set instructor foreign key
        instructor_id=inst_id,
    )
    # Stage new classroom entity in database session
    db.add(new_classroom)
    # Commit transaction to PostgreSQL database
    db.commit()
    # Refresh course instance from database
    db.refresh(new_course)

    # Check if cloud Supabase synchronization is enabled
    if settings.USE_SUPABASE:
        # Wrap Supabase sync in try-except block
        try:
            # Import Supabase client singleton dynamically
            from app.core.supabase import supabase
            # Upsert new course record to Supabase courses table
            supabase.table("courses").upsert({
                # Set course ID
                "id": new_course.id,
                # Set course name
                "name": new_course.name,
                # Set course code
                "code": new_course.code,
                # Set section
                "section": new_course.section,
                # Set UI color tone
                "tone": new_course.tone,
                # Set student count
                "students_count": new_course.students_count,
                # Set instructor ID
                "instructor_id": new_course.instructor_id,
            }).execute()
            # Upsert new classroom record to Supabase classrooms table
            supabase.table("classrooms").upsert({
                # Set classroom ID
                "id": new_course.id,
                # Set classroom name
                "name": new_course.name,
                # Set classroom code
                "code": new_course.code,
                # Set instructor ID
                "instructor_id": new_course.instructor_id,
            }).execute()
        # Catch synchronization errors
        except Exception as e:
            # Log warning message on cloud sync notice
            logger.warning(f"Cloud course/classroom sync notice: {e}")

    # Return serialized CourseResponse schema representation
    return CourseResponse(
        # Set course ID
        id=new_course.id,
        # Set course name
        name=new_course.name,
        # Set course code
        code=new_course.code,
        # Set section
        section=new_course.section,
        # Set UI color tone
        tone=new_course.tone,
        # Set initial student count
        students=new_course.students_count,
        # Set initial assignment count to zero
        assignments=0,
        # Set initial reviews count to zero
        reviews=0,
        # Set initial flags count to zero
        flags=0,
    )


# HTTP DELETE route handler deleting a course and cascading children
@router.delete("/{course_id}", status_code=204)
def delete_course(
    # Course ID string extracted from URL path parameter
    course_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing course deletion
    """Delete a course and all associated assignments and submissions."""
    # Query database for target course
    course = db.query(Course).filter(Course.id == course_id).first()
    # Check if target course does not exist
    if not course:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Course not found")

    # Verify authorization: instructor must own the course
    if course.instructor_id and instructor and instructor.id and course.instructor_id != instructor.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this course.",
        )

    # Also delete corresponding classroom if exists
    # Query database for corresponding classroom
    cl = db.query(Classroom).filter(Classroom.id == course_id).first()
    # Check if corresponding classroom exists
    if cl:
        # Delete classroom entity from session
        db.delete(cl)

    # Delete course entity from session (cascades to assignments/submissions)
    db.delete(course)
    # Commit transaction to PostgreSQL database
    db.commit()

    # Check if cloud Supabase synchronization is enabled
    if settings.USE_SUPABASE:
        # Wrap Supabase deletion in try-except block
        try:
            # Import Supabase client singleton dynamically
            from app.core.supabase import supabase
            # Delete course record from Supabase courses table
            supabase.table("courses").delete().eq("id", course_id).execute()
            # Delete classroom record from Supabase classrooms table
            supabase.table("classrooms").delete().eq("id", course_id).execute()
        # Catch synchronization errors
        except Exception as e:
            # Log warning message on cloud deletion failure
            logger.warning(f"Cloud course delete notice: {e}")

    # Return None for HTTP 204 No Content response
    return None


# HTTP GET route handler providing alias endpoint for course rubrics
@router.get("/{course_id}/rubrics")
def get_course_rubrics_alias(
    # Course ID string extracted from URL path parameter
    course_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing rubric alias retrieval
    """Retrieve all rubrics for a given course (alias for /rubrics/courses/{course_id}/rubrics)."""
    # Lazy import list_rubrics handler from rubrics module
    from app.api.v1.rubrics import list_rubrics
    # Delegate to list_rubrics handler with course ID
    return list_rubrics(classroom_id=course_id, course_id=course_id, db=db, current_instructor=instructor)
