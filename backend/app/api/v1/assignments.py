# Module docstring explaining the assignment API endpoints for CRUD and synchronization
"""Assignment API endpoints."""

# Import uuid library for generating unique assignment and course identifiers
import uuid
# Import typing annotations for list and optional values
from typing import List, Optional
# Import FastAPI routing constructs, dependency injection, and HTTP exceptions
from fastapi import APIRouter, Depends, HTTPException, status
# Import SQLAlchemy Session type for database operations
from sqlalchemy.orm import Session

# Import dependency helper to obtain a database session
from app.core.database import get_db
# Import Supabase client instance for remote synchronization
from app.core.supabase import supabase
# Import application logger for error and audit logging
from app.core.logging import logger
# Import Assignment SQLAlchemy model
from app.models.assignment import Assignment
# Import Course SQLAlchemy model
from app.models.course import Course
# Import Instructor SQLAlchemy model and auth dependency
from app.models.instructor import Instructor
from app.api.v1.auth import get_current_instructor
# Import assignment request and response Pydantic schemas
from app.schemas.assignment import AssignmentCreate, AssignmentResponse

# Initialize API router with OpenAPI tag for assignment operations
router = APIRouter(tags=["Assignments"])


# Route handler to retrieve all assignments for a specified course
@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentResponse])
# Define route function receiving course ID and database session dependency
def get_course_assignments(
    # Course ID string parameter from path
    course_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining retrieval of course assignments
    """Retrieve all assignments for a specified course."""
    # Query local database for assignments matching the course ID
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
    # Check if no assignments were found in the local database
    if not assignments:
        # Begin try block to sync assignments from Supabase
        try:
            # Import Supabase client
            from app.core.supabase import supabase
            # Query remote assignments table filtering by course ID
            res = supabase.table("assignments").select("*").eq("course_id", course_id).execute()
            # Check if remote assignments were returned
            if res.data:
                # Iterate through remote assignment records
                for a_data in res.data:
                    # Check if assignment does not already exist in local database
                    if not db.query(Assignment).filter(Assignment.id == a_data["id"]).first():
                        # Add new Assignment model to local database session
                        db.add(Assignment(
                            id=a_data["id"],
                            course_id=a_data["course_id"],
                            title=a_data["title"],
                            description=a_data.get("description"),
                            max_score=float(a_data.get("max_score", 100.0)),
                            rubric_id=a_data.get("rubric_id"),
                            reference_assignment_text=a_data.get("reference_assignment_text"),
                        ))
                # Commit mirrored assignments to local database
                db.commit()
                # Re-query local database for assignments
                assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()
        # Catch and log any errors during remote sync
        except Exception as e:
            # Log warning message regarding remote assignment sync notice
            logger.warning(f"Supabase assignments sync notice: {e}")
    # Return list of assignment records
    return assignments


# Helper function to ensure parent course exists in Supabase before child assignment creation
def _ensure_course_in_supabase(course: Course):
    # Docstring explaining foreign key synchronization for parent course
    """Ensures parent course exists in Supabase so foreign key constraints pass."""
    # Begin try block to check and insert parent course
    try:
        # Check if course exists in Supabase table
        c_res = supabase.table("courses").select("id").eq("id", course.id).execute()
        # If course does not exist in Supabase, insert it
        if not c_res.data:
            # Insert course record into Supabase
            supabase.table("courses").insert({
                "id": course.id,
                "name": course.name,
                "code": course.code,
                "section": course.section or "A",
                "tone": getattr(course, "tone", "lav"),
                "students_count": getattr(course, "students_count", 0),
            }).execute()
            # Log successful synchronization of parent course
            logger.info(f"Synchronized parent course {course.id} ({course.name}) to Supabase.")
    # Handle exception if course check/insert fails
    except Exception as e:
        # Log warning that parent course sync could not be completed
        logger.warning(f"Could not pre-sync course {course.id} to Supabase: {e}")


# Helper function to persist assignment record in local database and Supabase
def _persist_assignment_record(
    # Course model instance
    course: Course,
    # Assignment creation payload schema
    payload: AssignmentCreate,
    # Active database session
    db: Session,
) -> Assignment:
    # Docstring explaining assignment creation in local DB and Supabase
    """Internal helper to create assignment in local DB and Supabase."""
    # Generate unique assignment identifier with prefix
    assign_id = f"assign_{uuid.uuid4().hex[:12]}"
    # Instantiate Assignment model with request payload attributes
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
    # Add new assignment to local database session
    db.add(assignment)
    # Commit transaction to persist assignment in local database
    db.commit()
    # Refresh assignment instance to load default and generated attributes
    db.refresh(assignment)

    # 1. Ensure parent course exists in Supabase to fulfill foreign key
    # Synchronize parent course record to Supabase
    _ensure_course_in_supabase(course)

    # 2. Check if rubric_id exists in Supabase before attaching foreign key
    # Initialize rubric ID placeholder for Supabase
    sb_rubric_id = None
    # Check if assignment references a rubric ID
    if assignment.rubric_id:
        # Begin try block to check rubric existence in Supabase
        try:
            # Query Supabase for rubric with matching ID
            r_check = supabase.table("rubrics").select("id").eq("id", assignment.rubric_id).execute()
            # If rubric exists remotely, set remote rubric ID
            if r_check.data:
                # Assign valid rubric ID
                sb_rubric_id = assignment.rubric_id
        # Catch and ignore lookup errors, keeping rubric ID as None
        except Exception:
            # Set remote rubric ID to None if check fails
            sb_rubric_id = None

    # 3. Upsert assignment into Supabase
    # Begin try block to upsert assignment remotely
    try:
        # Upsert assignment record into Supabase assignments table
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
        # Log successful assignment persistence in Supabase
        logger.info(f"Persisted assignment {assignment.id} to Supabase successfully.")
    # Catch any remote synchronization errors
    except Exception as e:
        # Log warning notice for remote assignment sync failure
        logger.warning(f"Supabase assignment sync notice for {assignment.id}: {e}")

    # Return the newly persisted local assignment model
    return assignment


# Route handler to create an assignment under a specific course path
@router.post("/courses/{course_id}/assignments", response_model=AssignmentResponse)
# Define endpoint function accepting course ID, assignment payload, and db session
def create_course_assignment(
    # Course ID string parameter from path
    course_id: str,
    # Assignment creation schema from request body
    payload: AssignmentCreate,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining course assignment creation
    """Create a new assignment under a course with reference assignment support."""
    # Query local database for course by ID
    course = db.query(Course).filter(Course.id == course_id).first()
    # Check if course was not found locally
    if not course:
        # Check Supabase
        # Begin try block to search course in Supabase
        try:
            # Query Supabase for course by ID
            res = supabase.table("courses").select("*").eq("id", course_id).execute()
            # If course exists in Supabase, sync it locally
            if res.data:
                # Extract course data dictionary
                c_data = res.data[0]
                # Instantiate Course model from Supabase row
                course = Course(
                    id=c_data["id"],
                    name=c_data["name"],
                    code=c_data["code"],
                    section=c_data.get("section", "A"),
                    tone=c_data.get("tone", "lav"),
                    students_count=c_data.get("students_count", 0),
                )
                # Add course to local database session
                db.add(course)
                # Commit course to local database
                db.commit()
                # Refresh course entity
                db.refresh(course)
        # Catch and log any errors during remote course lookup
        except Exception as e:
            # Log warning notice for failed remote course lookup
            logger.warning(f"Supabase course lookup error: {e}")

    # If course is still not found, return 404 error
    if not course:
        # Raise HTTP 404 exception indicating course does not exist
        raise HTTPException(status_code=404, detail="Course not found")

    # Persist and return new assignment record
    return _persist_assignment_record(course=course, payload=payload, db=db)


# Direct assignment creation endpoint without course ID in path
@router.post("/assignments", response_model=AssignmentResponse)
# Define direct assignment creation endpoint function
def create_assignment_direct(
    # Assignment creation payload schema from request body
    payload: AssignmentCreate,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining direct assignment creation endpoint
    """Direct assignment creation endpoint (/api/v1/assignments).

    Accepts course_id in payload, defaulting to primary course if not provided.
    """
    # Extract course ID from request payload
    course_id = payload.course_id
    # Initialize course variable as None
    course = None
    # Check if course ID was provided in payload
    if course_id:
        # Query local database for course
        course = db.query(Course).filter(Course.id == course_id).first()
        # If course not found locally, attempt sync from Supabase
        if not course:
            # Begin try block to lookup course remotely
            try:
                # Query Supabase courses table by course ID
                res = supabase.table("courses").select("*").eq("id", course_id).execute()
                # If remote course data exists, create local Course model
                if res.data:
                    # Extract course data dictionary
                    c_data = res.data[0]
                    # Instantiate Course model
                    course = Course(
                        id=c_data["id"],
                        name=c_data["name"],
                        code=c_data["code"],
                        section=c_data.get("section", "A"),
                        tone=c_data.get("tone", "lav"),
                        students_count=c_data.get("students_count", 0),
                    )
                    # Add course to local database session
                    db.add(course)
                    # Commit course to local database
                    db.commit()
            # Catch lookup exceptions silently
            except Exception:
                # Ignore remote course lookup errors
                pass

    # If course is still None, fallback to first available course
    if not course:
        # Pick first available course
        # Query first available course in local database
        course = db.query(Course).first()
        # If no course exists at all, create a default course
        if not course:
            # Instantiate default Course model
            course = Course(
                id=f"c_{uuid.uuid4().hex[:8]}",
                name="Data Structures",
                code="CS201",
                section="A",
                tone="lav",
            )
            # Add default course to database session
            db.add(course)
            # Commit default course to database
            db.commit()

    # Persist and return new assignment record
    return _persist_assignment_record(course=course, payload=payload, db=db)


# Route handler to retrieve details for a specific assignment
@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
# Define route function receiving assignment ID and database session
def get_assignment_detail(
    # Assignment ID string parameter from path
    assignment_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining retrieval of assignment details
    """Retrieve single assignment details."""
    # Query local database for assignment by ID
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Check if assignment is not found locally
    if not assignment:
        # Begin try block to fetch assignment from Supabase
        try:
            # Import Supabase client
            from app.core.supabase import supabase
            # Query Supabase assignments table by ID
            res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
            # If assignment data is found remotely, mirror it locally
            if res.data:
                # Extract assignment data dictionary
                a_data = res.data[0]
                # Instantiate Assignment model
                assignment = Assignment(
                    id=a_data["id"],
                    course_id=a_data["course_id"],
                    title=a_data["title"],
                    description=a_data.get("description"),
                    max_score=float(a_data.get("max_score", 100.0)),
                    rubric_id=a_data.get("rubric_id"),
                    reference_assignment_text=a_data.get("reference_assignment_text"),
                )
                # Add assignment to local database session
                db.add(assignment)
                # Commit assignment to local database
                db.commit()
                # Refresh assignment instance
                db.refresh(assignment)
        # Handle exceptions during remote lookup
        except Exception as e:
            # Log warning notice for remote assignment lookup failure
            logger.warning(f"Supabase assignment detail sync notice: {e}")

    # Check if assignment was still not found
    if not assignment:
        # Raise HTTP 404 exception indicating assignment not found
        raise HTTPException(status_code=404, detail="Assignment not found")
    # Return assignment model instance
    return assignment


# Route handler to update an existing assignment
@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
# Define route function receiving assignment ID, update payload, and database session
def update_assignment(
    # Assignment ID string parameter from path
    assignment_id: str,
    # Assignment update schema from request body
    payload: AssignmentCreate,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining assignment update operation
    """Update assignment details, reference assignment text, or rubric."""
    # Query local database for assignment by ID
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Check if assignment does not exist
    if not assignment:
        # Raise HTTP 404 exception indicating assignment not found
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Update assignment title from payload
    assignment.title = payload.title
    # Check if description was provided in payload
    if payload.description is not None:
        # Update assignment description
        assignment.description = payload.description
    # Check if due date was provided in payload
    if payload.due_date is not None:
        # Update assignment due date
        assignment.due_date = payload.due_date
    # Check if max score was provided in payload
    if payload.max_score is not None:
        # Update assignment max score
        assignment.max_score = payload.max_score
    # Check if rubric ID was provided in payload
    if payload.rubric_id is not None:
        # Update assignment rubric ID
        assignment.rubric_id = payload.rubric_id
    # Check if reference assignment text was provided in payload
    if payload.reference_assignment_text is not None:
        # Update assignment reference solution text
        assignment.reference_assignment_text = payload.reference_assignment_text

    # Commit assignment changes to local database
    db.commit()
    # Refresh assignment instance with updated data
    db.refresh(assignment)

    # Begin try block to update assignment in Supabase
    try:
        # Update assignment row in Supabase table
        supabase.table("assignments").update({
            "title": assignment.title,
            "description": assignment.description,
            "max_score": assignment.max_score,
            "rubric_id": assignment.rubric_id,
            "reference_assignment_text": assignment.reference_assignment_text,
        }).eq("id", assignment.id).execute()
    # Catch any exceptions during remote update
    except Exception as e:
        # Log warning notice for remote assignment update failure
        logger.warning(f"Supabase assignment update notice: {e}")

    # Return updated assignment model instance
    return assignment


# Route handler to delete an assignment and associated records
@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete an assignment and cleanly cascade all its submissions, matches, and evaluations."""
    # Query database for assignment by ID
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Validate instructor ownership
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if (
        course
        and course.instructor_id
        and current_instructor
        and current_instructor.id
        and course.instructor_id != current_instructor.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this assignment.",
        )

    # Delete assignment (ORM cascading will remove submissions, similarity_matches, draft_grades)
    db.delete(assignment)
    db.commit()

    # Cloud Supabase synchronization if enabled
    if settings.USE_SUPABASE:
        try:
            supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
            supabase.table("assignments").delete().eq("id", assignment_id).execute()
        except Exception as e:
            logger.warning(f"Supabase assignment delete notice: {e}")

    return None
