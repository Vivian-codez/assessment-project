# Module docstring explaining the Classroom Roster and Roll Call Management API endpoints
"""Classroom Roster & Roll Call Management API endpoints (Local-first with optional cloud sync)."""

# Import standard csv library for parsing uploaded CSV rosters
import csv
# Import io module to handle in-memory text streams for CSV reading
import io
# Import uuid module for generating unique IDs for classrooms and students
import uuid
# Import typing annotations for lists, dictionaries, any, optionals, and unions
from typing import List, Dict, Any, Optional, Union
# Import FastAPI routing constructs, parameters, exceptions, uploads, and HTTP status codes
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status
# Import SQLAlchemy Session type for database operations
from sqlalchemy.orm import Session

# Import application settings instance
from app.core.config import settings
# Import get_db dependency helper to acquire database sessions
from app.core.database import get_db
# Import Supabase client instance for remote synchronization
from app.core.supabase import supabase
# Import application logger for debugging and notices
from app.core.logging import logger
# Import Classroom SQLAlchemy database model
from app.models.classroom import Classroom
# Import Student SQLAlchemy database model
from app.models.student import Student
# Import Submission SQLAlchemy database model for cascade handling
from app.models.submission import Submission
# Import Course SQLAlchemy database model
from app.models.course import Course
# Import classroom schemas for roster management and requests/responses
from app.schemas.classroom import (
    StudentItem,
    StudentResponse,
    StudentUploadCSVResponse,
    ClassroomCreate,
    ClassroomResponse,
)
# Import authentication dependency to resolve the authenticated instructor
from app.api.v1.auth import get_current_instructor
# Import Instructor SQLAlchemy database model
from app.models.instructor import Instructor

# Instantiate FastAPI APIRouter with /classrooms prefix and swagger tags
router = APIRouter(prefix="/classrooms", tags=["Classrooms & Roll Call"])


# Route handler to retrieve all classrooms for the active instructor
@router.get("", response_model=List[ClassroomResponse])
# Define endpoint function accepting db session and authenticated instructor dependency
def get_classrooms(
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected current authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining retrieval of classrooms with live student counts
    """Retrieve all classrooms for the active instructor with live student counts."""
    # Ensure any existing Course records have corresponding Classroom entries
    # Query all existing Course entities in local database
    courses = db.query(Course).all()
    # Iterate through courses to ensure corresponding Classroom records exist
    for crs in courses:
        # Check if a classroom with the same ID already exists
        existing_cl = db.query(Classroom).filter(Classroom.id == crs.id).first()
        # If no matching classroom exists, create one from the course
        if not existing_cl:
            # Instantiate new Classroom mirroring course properties
            new_cl = Classroom(
                id=crs.id,
                name=crs.name,
                code=crs.code,
                instructor_id=crs.instructor_id,
                created_at=crs.created_at,
            )
            # Add newly created classroom to database session
            db.add(new_cl)
    # Commit changes to persist synchronized classrooms
    db.commit()

    # Query all classrooms
    # Initialize base query for Classroom model
    query = db.query(Classroom)
    # Check if a valid current instructor with an ID is present
    if current_instructor and current_instructor.id:
        # Show all instructor classrooms or general
        # Query classrooms owned by this instructor or unassigned classrooms ordered by creation date
        inst_cls = query.filter((Classroom.instructor_id == current_instructor.id) | (Classroom.instructor_id == None)).order_by(Classroom.created_at.desc()).all()
        # Fall back to all classrooms if no instructor-specific classrooms are found
        classrooms = inst_cls if inst_cls else query.order_by(Classroom.created_at.desc()).all()
    # Fallback when no instructor filter applies
    else:
        # Retrieve all classrooms sorted by creation date in descending order
        classrooms = query.order_by(Classroom.created_at.desc()).all()

    # Optional cloud sync if enabled
    # Check if cloud synchronization is enabled via settings
    if settings.USE_SUPABASE:
        # Begin try block to sync classrooms from Supabase
        try:
            # Fetch remote classrooms from Supabase table
            res = supabase.table("classrooms").select("*").execute()
            # Iterate through rows returned by Supabase
            for row in (res.data or []):
                # Convert remote row ID to string
                r_id = str(row["id"])
                # Check if this classroom ID is already in the local classrooms list
                if not any(c.id == r_id for c in classrooms):
                    # Instantiate new Classroom model from remote data
                    new_c = Classroom(
                        id=r_id,
                        name=row["name"],
                        code=row["code"],
                        instructor_id=row.get("instructor_id"),
                    )
                    # Add new classroom to database session
                    db.add(new_c)
                    # Append new classroom to in-memory list
                    classrooms.append(new_c)
            # Commit newly synchronized remote classrooms to local database
            db.commit()
        # Catch any remote sync errors
        except Exception as e:
            # Log debug message for remote classroom sync notice
            logger.debug(f"Cloud classroom sync notice: {e}")

    # Initialize results list for formatted response items
    results = []
    # Iterate through all resolved classrooms
    for c in classrooms:
        # Count total enrolled students in this classroom
        st_count = db.query(Student).filter(Student.classroom_id == c.id).count()
        # Append formatted ClassroomResponse schema object to results
        results.append(
            ClassroomResponse(
                id=c.id,
                name=c.name,
                code=c.code,
                instructor_id=str(c.instructor_id or ""),
                students_count=st_count,
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
        )
    # Return list of formatted classroom responses
    return results


# Route handler to create a new classroom with 201 Created status
@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
# Define endpoint function accepting creation payload, db session, and authenticated instructor
def create_classroom(
    # Classroom creation payload from request body
    payload: ClassroomCreate,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining classroom creation
    """Create a new classroom / course for enrollment."""
    # Generate a unique string UUID for the new classroom
    c_id = str(uuid.uuid4())
    # Determine instructor ID from current authenticated user
    inst_id = current_instructor.id if current_instructor else None

    # Persist Classroom to local database
    # Instantiate new Classroom model
    new_classroom = Classroom(
        id=c_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        instructor_id=inst_id,
    )
    # Add new classroom to local database session
    db.add(new_classroom)

    # Also keep Course table synchronized for unified assignment workflows
    # Instantiate corresponding Course model
    new_course = Course(
        id=c_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        section="A",
        tone="lav",
        students_count=0,
        instructor_id=inst_id,
    )
    # Add new course to local database session
    db.add(new_course)
    # Commit transaction to save both classroom and course records
    db.commit()
    # Refresh classroom instance from database
    db.refresh(new_classroom)

    # Optional cloud sync if enabled
    # Check if Supabase cloud synchronization is enabled
    if settings.USE_SUPABASE:
        # Begin try block to sync to Supabase
        try:
            # Upsert classroom record in Supabase classrooms table
            supabase.table("classrooms").upsert({
                "id": c_id,
                "name": payload.name.strip(),
                "code": payload.code.strip(),
                "instructor_id": inst_id,
            }).execute()
            # Upsert corresponding course record in Supabase courses table
            supabase.table("courses").upsert({
                "id": c_id,
                "name": payload.name.strip(),
                "code": payload.code.strip(),
                "section": "A",
                "tone": "lav",
                "students_count": 0,
                "instructor_id": inst_id,
            }).execute()
        # Catch exceptions during cloud sync
        except Exception as e:
            # Log warning notice for failed cloud sync
            logger.warning(f"Cloud classroom sync notice: {e}")

    # Return newly created classroom response schema
    return ClassroomResponse(
        id=new_classroom.id,
        name=new_classroom.name,
        code=new_classroom.code,
        instructor_id=str(new_classroom.instructor_id or ""),
        students_count=0,
        created_at=new_classroom.created_at.isoformat() if new_classroom.created_at else "",
    )


# Route handler to retrieve details for a single classroom by ID
@router.get("/{classroom_id}", response_model=ClassroomResponse)
# Define endpoint function accepting classroom ID, db session, and authenticated instructor
def get_classroom(
    # Classroom ID path parameter
    classroom_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining retrieval of single classroom details
    """Retrieve details for a single classroom."""
    # Query local database for classroom by ID
    c = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    # Check if classroom was not found in Classroom table
    if not c:
        # Check if matching course exists
        # Query local database for course by ID
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        # If course exists, automatically create corresponding Classroom
        if crs:
            # Instantiate new Classroom from existing Course data
            c = Classroom(
                id=crs.id,
                name=crs.name,
                code=crs.code,
                instructor_id=crs.instructor_id,
                created_at=crs.created_at,
            )
            # Add new classroom to database session
            db.add(c)
            # Commit transaction to persist classroom
            db.commit()
            # Refresh classroom entity
            db.refresh(c)

    # Check if classroom still could not be found
    if not c:
        # Raise HTTP 404 exception indicating classroom not found
        raise HTTPException(status_code=404, detail="Classroom not found")

    # Count enrolled students for this classroom
    st_count = db.query(Student).filter(Student.classroom_id == c.id).count()
    # Return formatted ClassroomResponse schema
    return ClassroomResponse(
        id=c.id,
        name=c.name,
        code=c.code,
        instructor_id=str(c.instructor_id or ""),
        students_count=st_count,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


# Route handler to delete a classroom with 204 No Content status
@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
# Define endpoint function accepting classroom ID, db session, and authenticated instructor
def delete_classroom(
    # Classroom ID path parameter
    classroom_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining classroom deletion and cascading effects
    """Delete a classroom and cascade delete all its students and rubrics."""
    # Query local database for classroom by ID
    c = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    # If classroom exists, delete it from session
    if c:
        # Delete classroom record
        db.delete(c)
    # Query matching Course entity if present
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    # If matching course exists, delete it from session
    if crs:
        # Delete course record
        db.delete(crs)
    # Commit deletions to local database
    db.commit()

    # Check if Supabase cloud deletion is enabled
    if settings.USE_SUPABASE:
        # Begin try block to delete from Supabase
        try:
            # Delete students associated with this classroom in Supabase
            supabase.table("students").delete().eq("classroom_id", classroom_id).execute()
            # Delete rubrics associated with this classroom in Supabase
            supabase.table("rubrics").delete().eq("classroom_id", classroom_id).execute()
            # Delete classroom record in Supabase
            supabase.table("classrooms").delete().eq("id", classroom_id).execute()
        # Catch any remote deletion errors
        except Exception as e:
            # Log warning notice for cloud classroom delete failure
            logger.warning(f"Cloud classroom delete notice: {e}")

    # Return None for HTTP 204 No Content response
    return None


# ==============================================================================
# Student Roll Call Management
# ==============================================================================

# Route handler to manually enroll students into a classroom
@router.post("/{classroom_id}/students/manual")
# Define endpoint function accepting classroom ID, payload body, db session, and instructor
def enroll_students_manual(
    # Classroom ID path parameter
    classroom_id: str,
    # Student list or dictionary payload from request body
    payload: Union[List[StudentItem], Dict[str, Any]] = Body(...),
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining manual batch enrollment of students
    """Batch enroll students into a classroom either one-by-one or multi-line."""
    # Ensure classroom exists (or create from course)
    # Query local database for classroom by ID
    cl = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    # If classroom not found, check for matching Course
    if not cl:
        # Query course by ID
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        # If course exists, create Classroom model from course
        if crs:
            # Instantiate Classroom model
            cl = Classroom(id=crs.id, name=crs.name, code=crs.code, instructor_id=crs.instructor_id)
            # Add classroom to database session
            db.add(cl)
            # Commit transaction to persist classroom
            db.commit()
            # Refresh classroom entity
            db.refresh(cl)
        # If neither classroom nor course exists, raise 404
        else:
            # Raise HTTP 404 exception
            raise HTTPException(status_code=404, detail="Classroom not found")

    # Normalize input
    # Check if payload is already a list
    if isinstance(payload, list):
        # Use payload directly as student list
        students_raw = payload
    # Check if payload is a dict containing a 'students' key
    elif isinstance(payload, dict) and "students" in payload:
        # Extract students list from dictionary
        students_raw = payload["students"]
    # Handle single item payload
    else:
        # Wrap single item payload in a list
        students_raw = [payload]

    # Initialize list to track inserted or updated student records
    inserted_or_updated = []
    # Iterate over raw student entries
    for item in students_raw:
        # Handle StudentItem schema instance
        if isinstance(item, StudentItem):
            # Extract roll number string
            roll = item.roll_number.strip()
            # Extract full name string
            name = item.full_name.strip()
            # Extract email string or None
            email = item.email.strip() if item.email else None
        # Handle dictionary input
        elif isinstance(item, dict):
            # Extract roll number string from dictionary
            roll = str(item.get("roll_number", "")).strip()
            # Extract full name or name from dictionary
            name = str(item.get("full_name") or item.get("name", "")).strip()
            # Extract email string from dictionary or None
            email = str(item.get("email", "")).strip() or None
        # Skip unsupported data types
        else:
            # Continue to next item
            continue

        # Skip item if either roll number or name is empty
        if not roll or not name:
            # Continue to next item
            continue

        # Check if student with this roll number is already in the classroom
        existing = (
            db.query(Student)
            .filter(Student.classroom_id == classroom_id, Student.roll_number == roll)
            .first()
        )
        # If student already exists, update their record
        if existing:
            # Update existing student's full name
            existing.full_name = name
            # Check if email is provided
            if email:
                # Update existing student's email
                existing.email = email
            # Append updated student dictionary to results list
            inserted_or_updated.append({
                "id": existing.id,
                "classroom_id": classroom_id,
                "roll_number": roll,
                "full_name": name,
                "email": existing.email,
            })
        # If student does not exist, insert a new record
        else:
            # Generate new UUID for student
            st_id = str(uuid.uuid4())
            # Instantiate new Student model
            new_st = Student(
                id=st_id,
                classroom_id=classroom_id,
                roll_number=roll,
                full_name=name,
                email=email,
            )
            # Add new student to database session
            db.add(new_st)
            # Append newly created student dictionary to results list
            inserted_or_updated.append({
                "id": st_id,
                "classroom_id": classroom_id,
                "roll_number": roll,
                "full_name": name,
                "email": email,
            })

    # Commit all student insertions and updates to database
    db.commit()

    # Update student count on Course if linked
    # Query matching Course entity
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    # If course exists, update its students_count attribute
    if crs:
        # Count current students enrolled in classroom and update course
        crs.students_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
        # Commit updated student count to database
        db.commit()

    # Optional cloud sync
    # Check if Supabase cloud sync is enabled and records were processed
    if settings.USE_SUPABASE and inserted_or_updated:
        # Begin try block to upsert students in Supabase
        try:
            # Upsert students into Supabase handling roll number conflict
            supabase.table("students").upsert(inserted_or_updated, on_conflict="classroom_id,roll_number").execute()
        # Catch any exceptions during cloud sync
        except Exception as e:
            # Log warning notice for failed cloud student enrollment sync
            logger.warning(f"Cloud student enrollment sync notice: {e}")

    # Return summary dictionary with total inserted count and student list
    return {
        "status": "success",
        "total_inserted": len(inserted_or_updated),
        "students": inserted_or_updated,
    }


# Route handler to parse student roster from any file format (CSV, XLSX, PDF, DOCX, TXT, Images)
@router.post("/{classroom_id}/students/parse-roster")
async def parse_classroom_roster(
    classroom_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Accepts any file format (.csv, .xlsx, .xls, .pdf, .docx, .txt, or image scans) and extracts student records using heuristics and Gemini AI."""
    from app.services.roster_parser_service import roster_parser_service
    contents = await file.read()
    students = roster_parser_service.parse_roster_file(file.filename, contents)
    return {
        "status": "success",
        "filename": file.filename,
        "total_detected": len(students),
        "students": students,
    }


# Route handler to upload students roster via a CSV file or multi-format document
@router.post("/{classroom_id}/students/upload-csv", response_model=StudentUploadCSVResponse)
# Define asynchronous endpoint function receiving classroom ID, uploaded file, db session, and instructor
async def upload_students_csv(
    # Classroom ID path parameter
    classroom_id: str,
    # Uploaded multipart file
    file: UploadFile = File(...),
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Accepts a multipart roster (.csv, .xlsx, .pdf, .docx, .txt), parses student records, validates duplicates, and inserts."""
    from app.services.roster_parser_service import roster_parser_service

    # Read binary contents of uploaded file asynchronously
    contents = await file.read()

    # If non-csv file, use AI-powered multi-format parser directly
    if not file.filename.lower().endswith(".csv"):
        extracted = roster_parser_service.parse_roster_file(file.filename, contents)
        existing_rolls = {
            s.roll_number.strip()
            for s in db.query(Student).filter(Student.classroom_id == classroom_id).all()
            if s.roll_number
        }
        seen_rolls_in_file = set()
        inserted_records = []
        skipped = []
        for idx, item in enumerate(extracted, start=1):
            roll = item.get("roll_number", "").strip()
            name = item.get("full_name", "").strip()
            email = item.get("email", "").strip()
            if not roll or not name:
                skipped.append({"row": idx, "roll_number": roll, "full_name": name, "reason": "Missing roll number or name"})
                continue
            if roll in seen_rolls_in_file:
                skipped.append({"row": idx, "roll_number": roll, "full_name": name, "reason": f"Duplicate roll '{roll}' in file"})
                continue
            if roll in existing_rolls:
                skipped.append({"row": idx, "roll_number": roll, "full_name": name, "reason": f"Student '{roll}' already enrolled"})
                continue
            seen_rolls_in_file.add(roll)
            st_id = str(uuid.uuid4())
            new_student = Student(id=st_id, classroom_id=classroom_id, roll_number=roll, full_name=name, email=email or None)
            db.add(new_student)
            inserted_records.append({"id": st_id, "classroom_id": classroom_id, "roll_number": roll, "full_name": name, "email": email or None})
        db.commit()
        active_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        if crs:
            crs.students_count = active_count
            db.commit()
        return StudentUploadCSVResponse(
            status="success",
            total_inserted=len(inserted_records),
            total_skipped=len(skipped),
            students=[StudentResponse(id=r["id"], classroom_id=r["classroom_id"], roll_number=r["roll_number"], full_name=r["full_name"], email=r["email"]) for r in inserted_records],
            skipped=skipped,
        )
    # Try decoding file contents as UTF-8 with BOM support
    try:
        # Decode contents using UTF-8-sig
        text = contents.decode("utf-8-sig")
    # Fall back to Latin-1 encoding if UTF-8 decoding fails
    except UnicodeDecodeError:
        # Decode contents using Latin-1
        text = contents.decode("latin-1")

    # Wrap decoded text string in StringIO for csv reader consumption
    csv_file = io.StringIO(text)
    # Create CSV reader instance
    reader = csv.reader(csv_file)
    # Extract header row from CSV
    header = next(reader, None)

    # Check if header is missing or file is empty
    if not header:
        # Raise HTTP 400 Bad Request exception for empty CSV
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    # Initialize column index tracking variables
    roll_idx = None
    name_idx = None
    email_idx = None

    # Inspect header column names to find roll number, name, and email indices
    for idx, col in enumerate(header):
        # Normalize column header text for fuzzy matching
        c = col.strip().lower().replace("_", "").replace(" ", "").replace("-", "")
        # Check if normalized column matches roll number aliases
        if c in ("rollnumber", "rollno", "roll", "studentroll", "id", "roll#"):
            # Set roll number column index
            roll_idx = idx
        # Check if normalized column matches student name aliases
        elif c in ("name", "fullname", "studentname", "names"):
            # Set student name column index
            name_idx = idx
        # Check if normalized column matches email aliases
        elif c in ("email", "emailaddress", "studentemail", "mail"):
            # Set student email column index
            email_idx = idx

    # Verify that both roll number and name columns were found
    if roll_idx is None or name_idx is None:
        # Raise HTTP 400 Bad Request exception detailing missing columns
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain 'roll_number' and 'name' columns. Found columns: {', '.join(header)}",
        )

    # Fetch existing students in local DB
    # Create set of existing roll numbers enrolled in this classroom
    existing_rolls = {
        s.roll_number.strip()
        for s in db.query(Student).filter(Student.classroom_id == classroom_id).all()
        if s.roll_number
    }

    # Initialize set to track duplicate roll numbers within the current CSV file
    seen_rolls_in_file = set()
    # Initialize list of successfully inserted student records
    inserted_records = []
    # Initialize list of skipped row explanations
    skipped = []

    # Iterate through rows in CSV starting at line 2
    for row_num, row in enumerate(reader, start=2):
        # Skip empty rows or rows with only whitespace
        if not row or not any(cell.strip() for cell in row):
            # Continue to next row
            continue

        # Extract roll number string safely from row
        roll = row[roll_idx].strip() if roll_idx < len(row) else ""
        # Extract student name string safely from row
        name = row[name_idx].strip() if name_idx < len(row) else ""
        # Extract email string safely from row if column exists
        email = row[email_idx].strip() if email_idx is not None and email_idx < len(row) else ""

        # Skip row if roll number or name is empty
        if not roll or not name:
            # Record skipped row details
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": "Missing roll number or full name",
            })
            # Continue to next row
            continue

        # Check for duplicate roll number within the same CSV upload
        if roll in seen_rolls_in_file:
            # Record duplicate roll in file as skipped
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": f"Duplicate roll number '{roll}' found in CSV",
            })
            # Continue to next row
            continue

        # Check if student is already enrolled in the database
        if roll in existing_rolls:
            # Record existing student as skipped
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": f"Student with roll number '{roll}' is already enrolled",
            })
            # Continue to next row
            continue

        # Add roll number to seen set
        seen_rolls_in_file.add(roll)
        # Generate unique identifier for new student
        st_id = str(uuid.uuid4())
        # Instantiate Student database model
        new_student = Student(
            id=st_id,
            classroom_id=classroom_id,
            roll_number=roll,
            full_name=name,
            email=email or None,
        )
        # Add new student model to database session
        db.add(new_student)
        # Append record to inserted records list
        inserted_records.append({
            "id": st_id,
            "classroom_id": classroom_id,
            "roll_number": roll,
            "full_name": name,
            "email": email or None,
        })

    # Commit all inserted students to database
    db.commit()

    # Update course student count
    # Query linked course entity
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    # Check if linked course exists
    if crs:
        # Recalculate and update enrolled student count
        crs.students_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
        # Commit updated course count to database
        db.commit()

    # Optional cloud sync
    # Check if cloud sync is enabled and records were inserted
    if settings.USE_SUPABASE and inserted_records:
        # Begin try block to sync to Supabase
        try:
            # Upsert inserted students into Supabase table
            supabase.table("students").upsert(inserted_records, on_conflict="classroom_id,roll_number").execute()
        # Catch exceptions during cloud sync
        except Exception as e:
            # Log warning notice for failed CSV roster cloud sync
            logger.warning(f"Cloud CSV roster sync notice: {e}")

    # Return CSV upload response schema with insertion and skip details
    return StudentUploadCSVResponse(
        total_inserted=len(inserted_records),
        total_skipped=len(skipped),
        skipped=skipped,
        inserted=inserted_records,
    )


# Route handler to retrieve all students enrolled in a classroom
@router.get("/{classroom_id}/students", response_model=List[StudentResponse])
# Define endpoint function accepting classroom ID, db session, and authenticated instructor
def get_classroom_students(
    # Classroom ID path parameter
    classroom_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining retrieval of roll call list sorted by roll number
    """Retrieve complete enrolled roll call list sorted by roll_number."""
    # Query enrolled students sorted by roll number ascending
    students = (
        db.query(Student)
        .filter(Student.classroom_id == classroom_id)
        .order_by(Student.roll_number.asc())
        .all()
    )

    # Optional cloud fetch fallback if empty
    # Check if local list is empty and cloud sync is enabled
    if not students and settings.USE_SUPABASE:
        # Begin try block for fallback query
        try:
            # Query Supabase for students in this classroom ordered by roll number
            res = (
                supabase.table("students")
                .select("*")
                .eq("classroom_id", classroom_id)
                .order("roll_number")
                .execute()
            )
            # Iterate through retrieved student rows
            for s_data in (res.data or []):
                # Instantiate Student model from remote row data
                new_st = Student(
                    id=str(s_data["id"]),
                    classroom_id=str(s_data["classroom_id"]),
                    roll_number=str(s_data["roll_number"]),
                    full_name=str(s_data["full_name"]),
                    email=s_data.get("email"),
                )
                # Add student to local database session
                db.add(new_st)
                # Append student to in-memory list
                students.append(new_st)
            # Commit synchronized students to local database
            db.commit()
        # Catch fallback query exceptions
        except Exception as e:
            # Log debug notice for cloud student query notice
            logger.debug(f"Cloud students fallback query notice: {e}")

    # Format and return list of StudentResponse schema instances
    return [
        StudentResponse(
            id=s.id,
            classroom_id=s.classroom_id,
            roll_number=s.roll_number,
            full_name=s.full_name,
            email=s.email,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in students
    ]


# Route handler to delete an individual student from a classroom roster
@router.delete("/{classroom_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom_student(
    classroom_id: str,
    student_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete an enrolled student from a classroom roster and handle cascading dependencies cleanly."""
    # Verify target classroom exists
    cl = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cl:
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        if not crs:
            raise HTTPException(status_code=404, detail="Classroom not found")
        cl_inst_id = crs.instructor_id
    else:
        cl_inst_id = cl.instructor_id

    # Verify authorization: instructor owns classroom or classroom is unassigned
    if cl_inst_id and current_instructor and current_instructor.id and cl_inst_id != current_instructor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete students from this classroom.",
        )

    # Locate student record
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.classroom_id == classroom_id,
    ).first()

    if not student:
        # Fallback search by student_id
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found in this classroom")

    # Cleanly handle cascading dependencies: unlink student reference from submissions
    linked_subs = db.query(Submission).filter(Submission.student_id == student.id).all()
    for sub in linked_subs:
        sub.student_id = None

    # Delete student from database session
    db.delete(student)
    db.commit()

    # Recalculate and update enrolled student count on classroom and course
    active_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    if crs:
        crs.students_count = active_count
        db.commit()

    # Cloud Supabase synchronization if enabled
    if settings.USE_SUPABASE:
        try:
            supabase.table("students").delete().eq("id", student_id).eq("classroom_id", classroom_id).execute()
        except Exception as e:
            logger.warning(f"Cloud student delete notice: {e}")

    return None


# Direct route for student deletion
@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_direct(
    student_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete a student directly by ID and update parent classroom count."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return delete_classroom_student(
        classroom_id=student.classroom_id,
        student_id=student.id,
        db=db,
        current_instructor=current_instructor,
    )
