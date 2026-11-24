"""Submission, File Ingestion, and Batch Upload API endpoints.

Handles:
- Word document (.docx) extraction via python-docx with XML fallback
- Multi-format ingestion (.pdf, .txt, .docx, code, .zip archives)
- Raw file persistence into Supabase Storage bucket 'submissions' with public URL generation
- Text storage in database under extracted_text and content
- FERPA encryption on student identifiers
"""

# Import the os module for system utilities
import os
# Import the uuid module for system utilities
import uuid
# Import the zipfile module for system utilities
import zipfile
# Import BytesIO from io
from io import BytesIO
# Import datetime, timezone from datetime
from datetime import datetime, timezone
# Import List, Optional, Union from typing
from typing import List, Optional, Union
# Import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response, status, BackgroundTasks, Query from fastapi
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response, status, BackgroundTasks, Query
# Import Session from sqlalchemy.orm
from sqlalchemy.orm import Session

# Import get_db from app.core.database
from app.core.database import get_db
# Import logger, log_audit_event from app.core.logging
from app.core.logging import logger, log_audit_event
# Import Assignment from app.models.assignment
from app.models.assignment import Assignment
# Import Submission from app.models.submission
from app.models.submission import Submission
# Import SimilarityMatch and DraftGrade models for cascade deletion
from app.models.similarity_match import SimilarityMatch
from app.models.draft_grade import DraftGrade
from app.models.course import Course
from app.models.instructor import Instructor
from app.api.v1.auth import get_current_instructor
# Import BatchJob from app.models.batch_job
from app.models.batch_job import BatchJob
# Import schema and model definitions from app.schemas.submission
from app.schemas.submission import (
    # Import schema item SubmissionCreate
    SubmissionCreate,
    # Import schema item SubmissionResponse
    SubmissionResponse,
    # Import schema item BatchUploadResponse
    BatchUploadResponse,
    # Import schema item ClassroomBatchUploadResponse
    ClassroomBatchUploadResponse,
    # Import schema item ClassroomBatchUploadItem
    ClassroomBatchUploadItem,
    # Import schema item AssignStudentRequest
    AssignStudentRequest,
)
# Import pdf_service from app.services.pdf_service
from app.services.pdf_service import pdf_service
# Import supabase_service from app.services.supabase_service
from app.services.supabase_service import supabase_service
# Import student_resolver from app.services.resolver
from app.services.resolver import student_resolver
# Import is_redis_available from app.workers.celery_app
from app.workers.celery_app import is_redis_available
# Import evaluate_batch_task, run_evaluation_batch_logic from app.workers.evaluation_tasks
from app.workers.evaluation_tasks import evaluate_batch_task, run_evaluation_batch_logic
# Import get_current_instructor from app.api.v1.auth
from app.api.v1.auth import get_current_instructor
# Import Instructor from app.models.instructor
from app.models.instructor import Instructor

# Set router to APIRouter(tags=["Submissions"])
router = APIRouter(tags=["Submissions"])


# Define function to ensure assignment exists
def _ensure_assignment_exists(db: Session, assignment_id: str) -> Optional[Assignment]:
    """Ensure assignment exists in local DB, checking and replicating from Supabase if needed."""
    # Begin try block to execute operations safely
    try:
        # Set assignment to db.query(Assignment).filter(Assignment.id == assignment_id).first()
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        # Verify condition: assignment
        if assignment:
            # Return result: assignment
            return assignment

        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Import Course from app.models.course
        from app.models.course import Course
        # Set res to supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        # Verify condition: res.data
        if res.data:
            # Set a_data to res.data[0]
            a_data = res.data[0]
            # Set course_id to a_data["course_id"]
            course_id = a_data["course_id"]
            # Set course to db.query(Course).filter(Course.id == course_id).first()
            course = db.query(Course).filter(Course.id == course_id).first()
            # Verify condition: not course
            if not course:
                # Set c_res to supabase.table("courses").select("*").eq("id", course_id).execute()
                c_res = supabase.table("courses").select("*").eq("id", course_id).execute()
                # Verify condition: c_res.data
                if c_res.data:
                    # Set c_data to c_res.data[0]
                    c_data = c_res.data[0]
                    # Set course to Course(
                    course = Course(
                        # Execute statement: id=c_data["id"]
                        id=c_data["id"],
                        # Execute statement: name=c_data["name"]
                        name=c_data["name"],
                        # Execute statement: code=c_data["code"]
                        code=c_data["code"],
                        # Execute statement: section=c_data.get("section", "A")
                        section=c_data.get("section", "A"),
                        # Execute statement: tone=c_data.get("tone", "lav")
                        tone=c_data.get("tone", "lav"),
                        # Execute statement: students_count=c_data.get("students_count", 0)
                        students_count=c_data.get("students_count", 0),
                        # Execute statement: instructor_id=c_data.get("instructor_id")
                        instructor_id=c_data.get("instructor_id"),
                    # Execute statement: )
                    )
                    # Add entity record to database session
                    db.add(course)
                    # Commit transaction modifications to local database
                    db.commit()
            # Set assignment to Assignment(
            assignment = Assignment(
                # Execute statement: id=a_data["id"]
                id=a_data["id"],
                # Execute statement: course_id=course_id
                course_id=course_id,
                # Execute statement: title=a_data["title"]
                title=a_data["title"],
                # Execute statement: description=a_data.get("description")
                description=a_data.get("description"),
                # Execute statement: max_score=float(a_data.get("max_score", 100.0))
                max_score=float(a_data.get("max_score", 100.0)),
                # Execute statement: rubric_id=a_data.get("rubric_id")
                rubric_id=a_data.get("rubric_id"),
                # Execute statement: reference_assignment_text=a_data.get("reference_assignment_text")
                reference_assignment_text=a_data.get("reference_assignment_text"),
            # Execute statement: )
            )
            # Add entity record to database session
            db.add(assignment)
            # Commit transaction modifications to local database
            db.commit()
            # Execute statement: db.refresh(assignment)
            db.refresh(assignment)
            # Return result: assignment
            return assignment
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase assignment lookup fallback notice: {e}")

    # Dynamic fallback if not found anywhere: create the assignment so uploads never get rejected
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Import Course from app.models.course
        from app.models.course import Course
        # Set course to db.query(Course).first()
        course = db.query(Course).first()
        # Verify condition: not course
        if not course:
            # Do not auto-generate mock courses; require explicit teacher creation
            logger.warning("No existing course found during assignment lookup fallback; skipping auto-course generation.")
            return None

        # Pre-sync course to Supabase
        try:
            # Set c_chk to supabase.table("courses").select("id").eq("id", course.id).execute()
            c_chk = supabase.table("courses").select("id").eq("id", course.id).execute()
            # Verify condition: not c_chk.data
            if not c_chk.data:
                # Execute statement: supabase.table("courses").insert({
                supabase.table("courses").insert({
                    # Execute statement: "id": course.id
                    "id": course.id,
                    # Execute statement: "name": course.name
                    "name": course.name,
                    # Execute statement: "code": course.code
                    "code": course.code,
                    # Execute statement: "section": course.section or "A"
                    "section": course.section or "A",
                    # Execute statement: "tone": getattr(course, "tone", "lav")
                    "tone": getattr(course, "tone", "lav"),
                    # Execute statement: "students_count": getattr(course, "students_count", 0)
                    "students_count": getattr(course, "students_count", 0),
                # Execute statement: }).execute()
                }).execute()
        # Catch and handle exception: except Exception
        except Exception:
            # Placeholder pass statement
            pass

        # Set assignment to Assignment(
        assignment = Assignment(
            # Execute statement: id=assignment_id
            id=assignment_id,
            # Execute statement: course_id=course.id
            course_id=course.id,
            # Execute statement: title=f"Assignment {assignment_id}"
            title=f"Assignment {assignment_id}",
            # Execute statement: description="Active student assignment and reference solution."
            description="Active student assignment and reference solution.",
            # Execute statement: max_score=100.0
            max_score=100.0,
            # Execute statement: reference_assignment_text="Benchmark Reference Solution: Students must implement accurate algorithmic models, clean functional modularity, robust boundary test coverage, and comprehensive runtime complexity analysis."
            reference_assignment_text="Benchmark Reference Solution: Students must implement accurate algorithmic models, clean functional modularity, robust boundary test coverage, and comprehensive runtime complexity analysis.",
        # Execute statement: )
        )
        # Add entity record to database session
        db.add(assignment)
        # Commit transaction modifications to local database
        db.commit()
        # Execute statement: db.refresh(assignment)
        db.refresh(assignment)

        # Upsert into Supabase
        try:
            # Execute statement: supabase.table("assignments").upsert({
            supabase.table("assignments").upsert({
                # Execute statement: "id": assignment.id
                "id": assignment.id,
                # Execute statement: "course_id": assignment.course_id
                "course_id": assignment.course_id,
                # Execute statement: "title": assignment.title
                "title": assignment.title,
                # Execute statement: "description": assignment.description
                "description": assignment.description,
                # Execute statement: "max_score": assignment.max_score
                "max_score": assignment.max_score,
                # Execute statement: "reference_assignment_text": assignment.reference_assignment_text
                "reference_assignment_text": assignment.reference_assignment_text,
            # Execute statement: }).execute()
            }).execute()
            # Log informational message to runtime logger
            logger.info(f"Auto-created and synchronized assignment {assignment_id} to Supabase on upload.")
        # Catch and handle exception: except Exception as sb_err
        except Exception as sb_err:
            # Log warning notice message to runtime logger
            logger.warning(f"Supabase upload auto-assignment sync notice: {sb_err}")

        # Return result: assignment
        return assignment
    # Catch and handle exception: except Exception as create_err
    except Exception as create_err:
        # Log error notice message to runtime logger
        logger.error(f"Failed to auto-create assignment {assignment_id} on upload: {create_err}")
        # Return result: None
        return None


# Define function to create single submission
def _create_single_submission(
    # Execute statement: db: Session
    db: Session,
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Execute statement: filename: str
    filename: str,
    # Execute statement: content: bytes
    content: bytes,
    # Execute statement: upload_dir: str
    upload_dir: str,
    # Set custom_name: Optional[str] to None
    custom_name: Optional[str] = None,
    # Set custom_roll: Optional[str] to None
    custom_roll: Optional[str] = None,
    # Set custom_email: Optional[str] to None
    custom_email: Optional[str] = None,
# Execute statement: ) -> Submission
) -> Submission:
    """Helper to extract text with python-docx/pdf_service, upload raw file to Supabase Storage,

    and persist with FERPA encryption.
    """
    # Duplicate check for files
    import hashlib
    content_hash = hashlib.sha256(content).hexdigest() if content else ""
    existing_subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    for es in existing_subs:
        if es.file_name == filename and content:
            if es.file_path and os.path.exists(es.file_path):
                try:
                    with open(es.file_path, "rb") as ef:
                        if hashlib.sha256(ef.read()).hexdigest() == content_hash:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Duplicate upload: File '{filename}' has already been uploaded for this assignment."
                            )
                except HTTPException:
                    raise
                except Exception:
                    pass
            elif es.file_name == filename:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate upload: File '{filename}' has already been uploaded for this assignment."
                )

    # Set file_path to os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
    # Begin try block to execute operations safely
    try:
        # Manage context with: open(file_path, "wb") as f
        with open(file_path, "wb") as f:
            # Execute statement: f.write(content)
            f.write(content)
    # Catch and handle exception: except Exception as write_err
    except Exception as write_err:
        # Log warning notice message to runtime logger
        logger.warning(f"Local file write notice for {filename}: {write_err}")
        # Set file_path to ""
        file_path = ""

    # 1. Upload raw file to Supabase Storage bucket 'submissions' and obtain file_url
    file_url = None
    # Begin try block to execute operations safely
    try:
        # Set file_url to supabase_service.upload_file_to_storage(
        file_url = supabase_service.upload_file_to_storage(
            # Execute statement: file_bytes=content
            file_bytes=content,
            # Execute statement: file_name=filename
            file_name=filename,
            # Execute statement: assignment_id=assignment_id
            assignment_id=assignment_id,
        # Execute statement: )
        )
    # Catch and handle exception: except Exception as storage_err
    except Exception as storage_err:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase Storage persistence error for {filename}: {storage_err}")

    # 2. Determine file type and format file content string
    ext = filename.lower().split(".")[-1] if "." in filename else "text"
    # Set is_binary to ext in {"pdf", "docx", "doc", "zip", "png", "jpg", "jpeg", "tar", "gz"}
    is_binary = ext in {"pdf", "docx", "doc", "zip", "png", "jpg", "jpeg", "tar", "gz"}

    # Import the base64 module for system utilities
    import base64
    # Verify condition: not is_binary
    if not is_binary:
        # Begin try block to execute operations safely
        try:
            # Set file_content_str to content.decode("utf-8", errors="replace")
            file_content_str = content.decode("utf-8", errors="replace")
        # Catch and handle exception: except Exception
        except Exception:
            # Set file_content_str to base64.b64encode(content).decode("ascii")
            file_content_str = base64.b64encode(content).decode("ascii")
    # Handle alternative fallback path
    else:
        # Set file_content_str to base64.b64encode(content).decode("ascii")
        file_content_str = base64.b64encode(content).decode("ascii")

    # 3. Clean document extraction (python-docx for .docx, pdf_service for .pdf/.txt)
    extracted_text = pdf_service.extract_text_from_bytes(content, filename)
    # Verify condition: not extracted_text and not is_binary
    if not extracted_text and not is_binary:
        # Set extracted_text to file_content_str
        extracted_text = file_content_str

    # 4. Student metadata parsing & matching against course roll call
    student_id = None
    is_unmatched = False

    if custom_name and custom_name.strip():
        student_name = custom_name.strip()
        roll = custom_roll.strip() if (custom_roll and custom_roll.strip()) else "UNMATCHED"
        email = custom_email.strip() if (custom_email and custom_email.strip()) else f"{student_name.lower().replace(' ', '.')}@university.edu"
    else:
        # Load enrolled students for this assignment's course/classroom
        enrolled_students = []
        try:
            from app.models.student import Student
            assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            if assign:
                enrolled_students = db.query(Student).filter(
                    (Student.classroom_id == assign.course_id) | 
                    (Student.classroom_id == getattr(assign, "classroom_id", None))
                ).all()
        except Exception as e:
            logger.warning(f"Could not load enrolled students for submission matching: {e}")

        import re
        clean_stem = os.path.splitext(filename)[0]
        matched_student = None

        # Pass 1: Direct roll number match against enrolled students
        for s in enrolled_students:
            s_roll = s.roll_number.strip()
            if s_roll and re.search(r'(?i)(?:\b|[_\-\.\s])' + re.escape(s_roll) + r'(?:\b|[_\-\.\s])', clean_stem):
                matched_student = s
                break

        # Pass 2: Student full name or first+last name match
        if not matched_student:
            for s in enrolled_students:
                s_name = s.full_name.strip()
                if s_name:
                    name_clean = s_name.lower().replace("_", " ").replace("-", " ")
                    stem_clean = clean_stem.lower().replace("_", " ").replace("-", " ")
                    if name_clean in stem_clean:
                        matched_student = s
                        break
                    parts = name_clean.split()
                    if len(parts) >= 2 and parts[0] in stem_clean and parts[-1] in stem_clean:
                        matched_student = s
                        break

        # Pass 3: Extract roll-like token with regex and match
        if not matched_student:
            roll_candidates = re.findall(r'(?i)\b([a-z0-9]+[_\-][0-9]+|\d{2,8}|[a-z]{1,4}\d{2,6})\b', clean_stem)
            for cand in roll_candidates:
                if cand.lower() not in {"assignment", "assign", "sub", "submission", "task", "project", "homework", "hw", "final", "doc", "pdf"}:
                    for s in enrolled_students:
                        if s.roll_number.strip().lower() == cand.strip().lower():
                            matched_student = s
                            break
                    if matched_student:
                        break

        # Pass 4: Fallback match roll number or student name inside document text body
        if not matched_student and extracted_text:
            # Import text roll number extractor
            from app.services.resolver import extract_roll_number_from_text
            # Extract roll number from document body
            text_roll = extract_roll_number_from_text(extracted_text)
            # If roll number found in document text
            if text_roll:
                # Compare against enrolled students
                for s in enrolled_students:
                    # Match case-insensitively
                    if s.roll_number.strip().lower() == text_roll.lower():
                        # Set matched student
                        matched_student = s
                        # Break loop
                        break
            # Check student full name within document body if still unmatched
            if not matched_student:
                # Take sample of document text
                sample_txt = extracted_text[:3000].lower()
                # Iterate through enrolled students
                for s in enrolled_students:
                    # Check if student name appears in document
                    if s.full_name.strip() and s.full_name.strip().lower() in sample_txt:
                        # Match student
                        matched_student = s
                        # Break loop
                        break

        if matched_student:
            student_id = matched_student.id
            student_name = matched_student.full_name
            roll = matched_student.roll_number
            email = matched_student.email or f"{matched_student.full_name.lower().replace(' ', '.')}@university.edu"
            is_unmatched = False
        else:
            # Fallback regex extraction or unmatched
            candidate = None
            roll_candidates = re.findall(r'(?i)\b([a-z0-9]+[_\-][0-9]+|\d{2,8}|[a-z]{1,4}\d{2,6})\b', clean_stem)
            for cand in roll_candidates:
                if cand.lower() not in {"assignment", "assign", "sub", "submission", "task", "project", "homework", "hw", "final", "doc", "pdf"}:
                    candidate = cand
                    break
            roll = candidate if candidate else "UNMATCHED"
            # Filter out non-alphabetic tokens and common assignment/programming task words
            task_keywords = {
                "assignment", "submission", "doc", "project", "hw", "task", "final",
                "sort", "bubble", "search", "tree", "graph", "code", "lab", "test",
                "solution", "impl", "algorithm", "exercise", "ex", "homework"
            }
            # Extract name words excluding digits and assignment task tokens
            words = [w for w in clean_stem.replace("_", " ").replace("-", " ").split() if not any(c.isdigit() for c in w) and w.lower() not in task_keywords]
            
            # Common surnames to detect Last_First academic naming convention
            common_surnames = {
                "sharma", "singh", "kumar", "patel", "rao", "verma", "gupta", "das", "reddy",
                "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
                "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson",
                "thomas", "taylor", "moore", "jackson", "martin", "lee", "perez", "thompson",
                "white", "harris", "sanchez", "clark", "ramirez", "lewis", "robinson", "walker"
            }
            # Reconstruct standard First Last display name
            if len(words) == 2 and words[0].lower() in common_surnames:
                # Format as First Name then Last Name when uploaded as Last_First
                student_name = f"{words[1].capitalize()} {words[0].capitalize()}"
            elif words and any(len(w) > 1 for w in words):
                # Filter out single-letter noise words so files don't get renamed to "A"
                valid_words = [w for w in words if len(w) > 1]
                if valid_words:
                    student_name = " ".join([w.capitalize() for w in valid_words])
                else:
                    student_name = clean_stem.replace("_", " ").replace("-", " ").strip() or filename
            else:
                # Default to clean stem or original filename so identity is never lost
                student_name = clean_stem.replace("_", " ").replace("-", " ").strip() or filename

            # Sanity check: Never allow a single character (like "A") or generic placeholder
            if not student_name or len(student_name.strip()) <= 1 or student_name.strip().upper() in ("A", "UNMATCHED"):
                student_name = filename
            email = f"{clean_stem.lower().replace(' ', '.')}@university.edu"
            is_unmatched = (roll == "UNMATCHED")

    # Set sub to Submission(
    sub = Submission(
        # Execute statement: id=f"sub_{uuid.uuid4().hex[:8]}"
        id=f"sub_{uuid.uuid4().hex[:8]}",
        # Execute statement: assignment_id=assignment_id
        assignment_id=assignment_id,
        # Execute statement: student_id=student_id
        student_id=student_id,
        # Execute statement: student_identifier=f"{roll} - {student_name}"
        student_identifier=f"{roll} - {student_name}",
        # Execute statement: file_name=filename
        file_name=filename,
        # Execute statement: file_path=file_path
        file_path=file_path,
        # Execute statement: file_url=file_url
        file_url=file_url,
        # Execute statement: file_type=ext
        file_type=ext,
        # Execute statement: extracted_text=extracted_text
        extracted_text=extracted_text,
        # Execute statement: content=extracted_text or file_content_str
        content=extracted_text or file_content_str,
        # Execute statement: file_content=file_content_str
        file_content=file_content_str,
        # Execute statement: status="unmatched" if is_unmatched else "ready",
        status="unmatched" if is_unmatched else "ready",
    )
    # Uses FERPA transparent encryption setters
    sub.student_name = student_name
    # Set sub.student_roll to roll
    sub.student_roll = roll
    # Set sub.student_email to email
    sub.student_email = email

    # Add entity record to database session
    db.add(sub)
    # Return result: sub
    return sub


# Route handler handling HTTP POST requests
@router.post(
    # Execute statement: "/classrooms/{classroom_id}/assignments/{assignment_id}/batch-upload"
    "/classrooms/{classroom_id}/assignments/{assignment_id}/batch-upload",
    # Execute statement: response_model=ClassroomBatchUploadResponse
    response_model=ClassroomBatchUploadResponse,
    # Execute statement: status_code=status.HTTP_202_ACCEPTED
    status_code=status.HTTP_202_ACCEPTED,
# Execute statement: )
)
# Define asynchronous function to batch upload classroom assignment
async def batch_upload_classroom_assignment(
    # Execute statement: classroom_id: str
    classroom_id: str,
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Execute statement: background_tasks: BackgroundTasks
    background_tasks: BackgroundTasks,
    # Set file: Optional[UploadFile] to File(None)
    file: Optional[UploadFile] = File(None),
    # Set files: Optional[List[UploadFile]] to File(None)
    files: Optional[List[UploadFile]] = File(None),
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
# Execute statement: )
):
    """Batch upload student submissions for an assignment within a classroom.

    Accepts ZIP archive or multi-file payload, extracts in-memory, uploads to
    Supabase Storage bucket 'submissions', resolves roll numbers against classroom
    roster in Supabase, inserts submissions, and non-blockingly dispatches Celery
    background evaluation. Returns HTTP 202 with batch_job_id immediately.
    """
    # Set assignment to _ensure_assignment_exists(db, assignment_id)
    assignment = _ensure_assignment_exists(db, assignment_id)
    # Verify condition: not assignment
    if not assignment:
        # Raise error condition: HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")
        raise HTTPException(status_code=404, detail=f"Assignment {assignment_id} not found")

    # 1. Gather all incoming file payloads
    incoming_files: List[UploadFile] = []
    # Verify condition: file
    if file:
        # Execute statement: incoming_files.append(file)
        incoming_files.append(file)
    # Verify condition: files
    if files:
        # Execute statement: incoming_files.extend(files)
        incoming_files.extend(files)

    # Verify condition: not incoming_files
    if not incoming_files:
        # Raise error condition: HTTPException(
        raise HTTPException(
            # Execute statement: status_code=status.HTTP_400_BAD_REQUEST
            status_code=status.HTTP_400_BAD_REQUEST,
            # Execute statement: detail="No files provided. Please upload a ZIP archive or submission files."
            detail="No files provided. Please upload a ZIP archive or submission files.",
        # Execute statement: )
        )

    # 2. Extract in-memory without saving temporary junk to disk
    extracted_entries: List[tuple[str, bytes]] = []

    # Iterate through: up_file in incoming_files
    for up_file in incoming_files:
        # Set original_name to up_file.filename or "submission.bin"
        original_name = up_file.filename or "submission.bin"
        # Begin try block to execute operations safely
        try:
            # Set content_bytes to await up_file.read()
            content_bytes = await up_file.read()
        # Catch and handle exception: except Exception as read_err
        except Exception as read_err:
            # Log error notice message to runtime logger
            logger.error(f"Failed to read upload payload {original_name}: {read_err}")
            # Skip remaining block and continue to next iteration
            continue

        # Verify condition: not content_bytes
        if not content_bytes:
            # Skip remaining block and continue to next iteration
            continue

        # Verify condition: original_name.lower().endswith(".zip")
        if original_name.lower().endswith(".zip"):
            # Begin try block to execute operations safely
            try:
                # Manage context with: zipfile.ZipFile(BytesIO(content_bytes)) as zf
                with zipfile.ZipFile(BytesIO(content_bytes)) as zf:
                    # Verify condition: zf.testzip() is not None
                    if zf.testzip() is not None:
                        # Raise error condition: HTTPException(
                        raise HTTPException(
                            # Execute statement: status_code=status.HTTP_400_BAD_REQUEST
                            status_code=status.HTTP_400_BAD_REQUEST,
                            # Execute statement: detail=f"Corrupted or invalid ZIP archive: {original_name}"
                            detail=f"Corrupted or invalid ZIP archive: {original_name}",
                        # Execute statement: )
                        )
                    # Iterate through: member in zf.infolist()
                    for member in zf.infolist():
                        # Verify condition: member.is_dir()
                        if member.is_dir():
                            # Skip remaining block and continue to next iteration
                            continue
                        # Set base_fname to os.path.basename(member.filename)
                        base_fname = os.path.basename(member.filename)
                        # Filter system artifacts with safe string guards
                        if not base_fname or (isinstance(base_fname, str) and base_fname.startswith(".")) or (isinstance(member.filename, str) and member.filename.startswith("__MACOSX")):
                            # Skip remaining block and continue to next iteration
                            continue
                        # Set inner_bytes to zf.read(member.filename)
                        inner_bytes = zf.read(member.filename)
                        # Verify condition: inner_bytes
                        if inner_bytes:
                            # Execute statement: extracted_entries.append((base_fname, inner_bytes))
                            extracted_entries.append((base_fname, inner_bytes))
            # Catch and handle exception: except zipfile.BadZipFile
            except zipfile.BadZipFile:
                # Raise error condition: HTTPException(
                raise HTTPException(
                    # Execute statement: status_code=status.HTTP_400_BAD_REQUEST
                    status_code=status.HTTP_400_BAD_REQUEST,
                    # Execute statement: detail=f"The uploaded file '{original_name}' is not a valid ZIP archive."
                    detail=f"The uploaded file '{original_name}' is not a valid ZIP archive.",
                # Execute statement: )
                )
        # Handle alternative fallback path
        else:
            # Set base_fname to os.path.basename(original_name)
            base_fname = os.path.basename(original_name)
            # Execute statement: extracted_entries.append((base_fname, content_bytes))
            extracted_entries.append((base_fname, content_bytes))

    # Verify condition: not extracted_entries
    if not extracted_entries:
        # Raise error condition: HTTPException(
        raise HTTPException(
            # Execute statement: status_code=status.HTTP_400_BAD_REQUEST
            status_code=status.HTTP_400_BAD_REQUEST,
            # Execute statement: detail="No valid student submission files found in the uploaded payload."
            detail="No valid student submission files found in the uploaded payload.",
        # Execute statement: )
        )

    # 3. Build roster index for fast O(1) resolution across the batch
    roster_index = student_resolver.get_classroom_roster_index(classroom_id)

    # Set created_submissions: List[Submission] to []
    created_submissions: List[Submission] = []
    # Set queued_items: List[ClassroomBatchUploadItem] to []
    queued_items: List[ClassroomBatchUploadItem] = []
    # Set unmatched_items: List[ClassroomBatchUploadItem] to []
    unmatched_items: List[ClassroomBatchUploadItem] = []
    # Set queued_submission_ids: List[str] to []
    queued_submission_ids: List[str] = []

    # Iterate through: fname, fbytes in extracted_entries
    for fname, fbytes in extracted_entries:
        # Set sub_id to f"sub_{uuid.uuid4().hex[:12]}"
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"

        # a. Save raw asset to Supabase Storage 'submissions/' bucket
        file_url = None
        # Begin try block to execute operations safely
        try:
            # Set file_url to supabase_service.upload_file_to_storage(
            file_url = supabase_service.upload_file_to_storage(
                # Execute statement: file_bytes=fbytes
                file_bytes=fbytes,
                # Execute statement: file_name=fname
                file_name=fname,
                # Execute statement: assignment_id=assignment_id
                assignment_id=assignment_id,
            # Execute statement: )
            )
        # Catch and handle exception: except Exception as storage_err
        except Exception as storage_err:
            # Log warning notice message to runtime logger
            logger.warning(f"Supabase Storage persistence notice for {fname}: {storage_err}")

        # b. In-memory clean document text/code extraction
        ext = fname.lower().split(".")[-1] if "." in fname else "text"
        # Set is_binary to ext in binary file formats
        is_binary = ext in {"pdf", "docx", "doc", "zip", "png", "jpg", "jpeg"}
        # Extract text using pdf_service
        extracted_text = pdf_service.extract_text_from_bytes(fbytes, fname)
        # Verify condition: not extracted_text and not is_binary
        if not extracted_text and not is_binary:
            # Begin try block to decode text files
            try:
                # Decode bytes to utf-8
                extracted_text = fbytes.decode("utf-8", errors="replace")
            # Catch decode exception
            except Exception:
                # Default to empty string
                extracted_text = ""

        # c. Resolve roll number and match to enrolled student in classroom (with body text fallback)
        student_id, sub_status, student_match, detected_roll = student_resolver.resolve_submission_file(
            # Classroom identifier
            classroom_id=classroom_id,
            # Uploaded file name
            filename=fname,
            # Pre-indexed roster dictionary
            roster_index=roster_index,
            # Extracted plain text content for fallback roll matching
            text_content=extracted_text,
        )

        # Verify condition: student_match
        if student_match:
            # Set sub_status to "ready" (extracted and matched; awaiting teacher command to start AI grading)
            sub_status = "ready"
            # Set student_id to str(student_match.get("id"))
            student_id = str(student_match.get("id"))
            # Set student_name to student_match.get("full_name") or student_match.get("name") or f"Student {detected_roll}"
            student_name = student_match.get("full_name") or student_match.get("name") or f"Student {detected_roll}"
            # Set student_roll to student_match.get("roll_number") or detected_roll
            student_roll = student_match.get("roll_number") or detected_roll
            # Set student_email to student_match.get("email") or f"{student_roll}@university.edu"
            student_email = student_match.get("email") or f"{student_roll}@university.edu"
        # Handle alternative fallback path
        else:
            # Set sub_status to "unmatched"
            sub_status = "unmatched"
            # Set student_id to None
            student_id = None
            # Set student_roll to detected_roll
            student_roll = detected_roll
            # Set student_name to f"Roll {detected_roll}" if detected_roll else f"Unmatched ({fname})"
            student_name = f"Roll {detected_roll}" if detected_roll else f"Unmatched ({fname})"
            # Set student_email to f"unmatched_{sub_id[:8]}@university.edu"
            student_email = f"unmatched_{sub_id[:8]}@university.edu"

        # d. Create Submission model
        sub = Submission(
            # Execute statement: id=sub_id
            id=sub_id,
            # Execute statement: classroom_id=classroom_id
            classroom_id=classroom_id,
            # Execute statement: assignment_id=assignment_id
            assignment_id=assignment_id,
            # Execute statement: student_id=student_id
            student_id=student_id,
            # Execute statement: file_name=fname
            file_name=fname,
            # Execute statement: file_path="",  # Memory-only extraction without temporary file clutter
            file_path="",  # Memory-only extraction without temporary file clutter
            # Execute statement: file_url=file_url
            file_url=file_url,
            # Execute statement: file_type=ext
            file_type=ext,
            # Execute statement: extracted_text=extracted_text
            extracted_text=extracted_text,
            # Execute statement: content=extracted_text or ""
            content=extracted_text or "",
            # Execute statement: file_content=extracted_text or ""
            file_content=extracted_text or "",
            # Execute statement: status=sub_status
            status=sub_status,
        # Execute statement: )
        )
        # Set sub.student_name to student_name
        sub.student_name = student_name
        # Set sub.student_roll to student_roll or "UNASSIGNED"
        sub.student_roll = student_roll or "UNASSIGNED"
        # Set sub.student_email to student_email
        sub.student_email = student_email
        # Add entity record to database session
        db.add(sub)
        # Execute statement: created_submissions.append(sub)
        created_submissions.append(sub)

        # e. Item for HTTP response
        item = ClassroomBatchUploadItem(
            # Execute statement: id=sub_id
            id=sub_id,
            # Execute statement: file_name=fname
            file_name=fname,
            # Execute statement: student_id=student_id
            student_id=student_id,
            # Execute statement: roll_number=student_roll
            roll_number=student_roll,
            # Execute statement: student_name=student_name
            student_name=student_name,
            # Execute statement: status=sub_status
            status=sub_status,
            # Execute statement: file_url=file_url
            file_url=file_url,
        # Execute statement: )
        )

        # Verify condition: sub_status in ("ready", "queued")
        if sub_status in ("ready", "queued"):
            # Execute statement: queued_items.append(item)
            queued_items.append(item)
            # Execute statement: queued_submission_ids.append(sub_id)
            queued_submission_ids.append(sub_id)
        # Handle alternative fallback path
        else:
            # Execute statement: unmatched_items.append(item)
            unmatched_items.append(item)

    # 4. Batch insert into database and synchronize to Supabase
    try:
        # Commit transaction modifications to local database
        db.commit()
    # Catch and handle exception: except Exception as db_err
    except Exception as db_err:
        # Rollback database transaction on error
        db.rollback()
        # Log error notice message to runtime logger
        logger.error(f"Database commit error for batch submissions: {db_err}")
        # Raise error condition: HTTPException(status_code=500, detail="Database persistence error during batch upload")
        raise HTTPException(status_code=500, detail="Database persistence error during batch upload")

    # Begin try block to execute operations safely
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Set supabase_records to [
        supabase_records = [
            # Execute statement: {
            {
                # Execute statement: "id": s.id
                "id": s.id,
                # Execute statement: "classroom_id": s.classroom_id
                "classroom_id": s.classroom_id,
                # Execute statement: "assignment_id": s.assignment_id
                "assignment_id": s.assignment_id,
                # Execute statement: "student_id": s.student_id
                "student_id": s.student_id,
                # Execute statement: "student_name_encrypted": s.student_name_encrypted
                "student_name_encrypted": s.student_name_encrypted,
                # Execute statement: "student_roll_encrypted": s.student_roll_encrypted
                "student_roll_encrypted": s.student_roll_encrypted,
                # Execute statement: "student_email_encrypted": s.student_email_encrypted
                "student_email_encrypted": s.student_email_encrypted,
                # Execute statement: "file_name": s.file_name
                "file_name": s.file_name,
                # Execute statement: "file_path": s.file_path
                "file_path": s.file_path,
                # Execute statement: "file_url": s.file_url
                "file_url": s.file_url,
                # Execute statement: "file_type": s.file_type
                "file_type": s.file_type,
                # Execute statement: "extracted_text": s.extracted_text
                "extracted_text": s.extracted_text,
                # Execute statement: "content": s.content or s.extracted_text or ""
                "content": s.content or s.extracted_text or "",
                # Execute statement: "file_content": s.file_content
                "file_content": s.file_content,
                # Execute statement: "similarity_score": 0.0
                "similarity_score": 0.0,
                # Execute statement: "ai_content_probability": 0.0
                "ai_content_probability": 0.0,
                # Execute statement: "web_plagiarism_score": 0.0
                "web_plagiarism_score": 0.0,
                # Execute statement: "web_sources": []
                "web_sources": [],
                # Execute statement: "status": s.status
                "status": s.status,
            # Execute statement: }
            }
            # Execute statement: for s in created_submissions
            for s in created_submissions
        # Execute statement: ]
        ]
        # Execute statement: supabase.table("submissions").upsert(supabase_records).execute()
        supabase.table("submissions").upsert(supabase_records).execute()
        # Log informational message to runtime logger
        logger.info(f"Synchronized {len(supabase_records)} batch submissions to Supabase.")
    # Catch and handle exception: except Exception as sb_err
    except Exception as sb_err:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase submissions batch sync notice: {sb_err}")

    # 5. Non-Blocking Enqueue via Celery Background Task (Redis broker)
    batch_job_id = f"job_{uuid.uuid4().hex[:12]}"
    # Set total_evaluable to len(queued_submission_ids)
    total_evaluable = len(queued_submission_ids)

    # Register batch job record
    job_record = BatchJob(
        # Execute statement: id=batch_job_id
        id=batch_job_id,
        # Execute statement: assignment_id=assignment_id
        assignment_id=assignment_id,
        # Execute statement: status="ready" if total_evaluable > 0 else "completed",
        status="ready" if total_evaluable > 0 else "completed",
        # Execute statement: progress_pct=100.0,
        progress_pct=100.0,
        # Execute statement: total_items=total_evaluable,
        total_items=total_evaluable,
        # Execute statement: processed_items=total_evaluable,
        processed_items=total_evaluable,
    # Execute statement: )
    )
    # Add entity record to database session
    db.add(job_record)
    # Commit transaction modifications to local database
    db.commit()

    # Submissions sit in status 'ready' per rule 1: AI auto-grading is never dispatched automatically upon upload
    logger.info(f"Submissions for assignment {assignment_id} sitting in status 'ready'. Awaiting teacher-controlled grading start.")

    # Return result: ClassroomBatchUploadResponse(
    return ClassroomBatchUploadResponse(
        # Execute statement: batch_job_id=batch_job_id
        batch_job_id=batch_job_id,
        # Execute statement: total=len(created_submissions)
        total=len(created_submissions),
        # Execute statement: queued_submissions=queued_items
        queued_submissions=queued_items,
        # Execute statement: unmatched_submissions=unmatched_items
        unmatched_submissions=unmatched_items,
        # Execute statement: status="queued" if total_evaluable > 0 else "completed"
        status="queued" if total_evaluable > 0 else "completed",
    # Execute statement: )
    )


# Route handler handling HTTP POST requests
@router.post("/assignments/{assignment_id}/submissions/batch-upload", response_model=BatchUploadResponse)
# Define asynchronous function to batch upload submissions
async def batch_upload_submissions(
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Set files: List[UploadFile] to File(...)
    files: List[UploadFile] = File(...),
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
    # Set instructor: Instructor to Depends(get_current_instructor)
    instructor: Instructor = Depends(get_current_instructor),
# Execute statement: )
):
    """Batch upload student submissions (.docx, .pdf, .txt, code, and .zip archives).

    Extracts text using python-docx and pdf_service, saves raw files to Supabase Storage,
    and synchronizes records to the Supabase database.
    """
    # Set assignment to _ensure_assignment_exists(db, assignment_id)
    assignment = _ensure_assignment_exists(db, assignment_id)
    # Verify condition: not assignment
    if not assignment:
        # Raise error condition: HTTPException(status_code=404, detail="Assignment not found")
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Set batch_id to f"batch_{uuid.uuid4().hex[:8]}"
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    # Set uploaded_names to []
    uploaded_names = []
    # Set created_submissions to []
    created_submissions = []

    # Set upload_dir to os.path.join(os.getcwd(), "uploads", assignment_id)
    upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
    # Execute statement: os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    # Iterate through: file in files
    for file in files:
        # Set filename to file.filename
        filename = file.filename
        # Set content to await file.read()
        content = await file.read()

        # Handle zip bundle extraction
        if filename.lower().endswith(".zip"):
            # Begin try block to execute operations safely
            try:
                # Manage context with: zipfile.ZipFile(BytesIO(content)) as zf
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    # Iterate through: zip_info in zf.infolist()
                    for zip_info in zf.infolist():
                        # Verify condition: not zip_info.is_dir() and safe filename check
                        if not zip_info.is_dir() and not (isinstance(zip_info.filename, str) and zip_info.filename.startswith("__MACOSX")):
                            # Set extracted_bytes to zf.read(zip_info.filename)
                            extracted_bytes = zf.read(zip_info.filename)
                            # Set inner_name to os.path.basename(zip_info.filename)
                            inner_name = os.path.basename(zip_info.filename)
                            # Set sub to _create_single_submission(
                            sub = _create_single_submission(
                                # Execute statement: db, assignment_id, inner_name, extracted_bytes, upload_dir
                                db, assignment_id, inner_name, extracted_bytes, upload_dir
                            # Execute statement: )
                            )
                            # Execute statement: uploaded_names.append(inner_name)
                            uploaded_names.append(inner_name)
                            # Execute statement: created_submissions.append(sub)
                            created_submissions.append(sub)
            # Catch and handle exception: except Exception as e
            except Exception as e:
                # Log error notice message to runtime logger
                logger.error(f"Error extracting zip archive {filename}: {e}")
                # Skip remaining block and continue to next iteration
                continue
        # Handle alternative fallback path
        else:
            # Set sub to _create_single_submission(db, assignment_id, filename, content, upload_dir)
            sub = _create_single_submission(db, assignment_id, filename, content, upload_dir)
            # Execute statement: uploaded_names.append(filename)
            uploaded_names.append(filename)
            # Execute statement: created_submissions.append(sub)
            created_submissions.append(sub)

    # Begin try block to execute operations safely
    try:
        # Commit transaction modifications to local database
        db.commit()
    # Catch and handle exception: except Exception as db_err
    except Exception as db_err:
        # Rollback database transaction on error
        db.rollback()
        # Log error notice message to runtime logger
        logger.error(f"Database commit error in batch upload: {db_err}")
        # Raise error condition: HTTPException(status_code=500, detail="Database persistence error during batch upload")
        raise HTTPException(status_code=500, detail="Database persistence error during batch upload")

    # Sync created submissions to Supabase database (storage & tables)
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Set supabase_records to [
        supabase_records = [
            # Execute statement: {
            {
                # Execute statement: "id": s.id
                "id": s.id,
                # Execute statement: "assignment_id": s.assignment_id
                "assignment_id": s.assignment_id,
                # Execute statement: "student_name_encrypted": s.student_name_encrypted
                "student_name_encrypted": s.student_name_encrypted,
                # Execute statement: "student_roll_encrypted": s.student_roll_encrypted
                "student_roll_encrypted": s.student_roll_encrypted,
                # Execute statement: "student_email_encrypted": s.student_email_encrypted
                "student_email_encrypted": s.student_email_encrypted,
                # Execute statement: "file_name": s.file_name
                "file_name": s.file_name,
                # Execute statement: "file_path": s.file_path
                "file_path": s.file_path,
                # Execute statement: "file_url": s.file_url
                "file_url": s.file_url,
                # Execute statement: "file_type": s.file_type
                "file_type": s.file_type,
                # Execute statement: "extracted_text": s.extracted_text
                "extracted_text": s.extracted_text,
                # Execute statement: "content": s.content or s.extracted_text or ""
                "content": s.content or s.extracted_text or "",
                # Execute statement: "file_content": s.file_content
                "file_content": s.file_content,
                # Execute statement: "similarity_score": 0.0
                "similarity_score": 0.0,
                # Execute statement: "ai_content_probability": 0.0
                "ai_content_probability": 0.0,
                # Execute statement: "web_plagiarism_score": 0.0
                "web_plagiarism_score": 0.0,
                # Execute statement: "web_sources": []
                "web_sources": [],
                # Execute statement: "status": s.status
                "status": s.status,
            # Execute statement: }
            }
            # Execute statement: for s in created_submissions
            for s in created_submissions
        # Execute statement: ]
        ]
        # Verify condition: supabase_records
        if supabase_records:
            # Execute statement: supabase.table("submissions").upsert(supabase_records).execute()
            supabase.table("submissions").upsert(supabase_records).execute()
            # Log informational message to runtime logger
            logger.info(f"Synchronized {len(supabase_records)} submissions with Supabase database.")
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase batch submission sync notice: {e}")

    # Record structured audit log event for compliance
    log_audit_event(
        # Execute statement: actor=instructor.name
        actor=instructor.name,
        # Execute statement: action="BATCH_UPLOAD"
        action="BATCH_UPLOAD",
        # Execute statement: entity="Assignment"
        entity="Assignment",
        # Execute statement: entity_id=assignment_id
        entity_id=assignment_id,
        # Execute statement: details=f"Uploaded {len(created_submissions)} files in batch {batch_id}"
        details=f"Uploaded {len(created_submissions)} files in batch {batch_id}",
    # Execute statement: )
    )

    # Set responses to [
    responses = [
        # Execute statement: SubmissionResponse(
        SubmissionResponse(
            # Execute statement: id=s.id
            id=s.id,
            # Execute statement: assignment_id=s.assignment_id
            assignment_id=s.assignment_id,
            # Execute statement: student=s.student_name
            student=s.student_name,
            # Execute statement: roll=s.student_roll
            roll=s.student_roll,
            # Execute statement: file_name=s.file_name
            file_name=s.file_name,
            # Execute statement: status=s.status
            status=s.status,
            # Execute statement: score=s.draft_grade.suggested_score if s.draft_grade else None
            score=s.draft_grade.suggested_score if s.draft_grade else None,
            # Execute statement: similarity=s.similarity_score
            similarity=s.similarity_score,
            # Execute statement: ai_content=s.ai_content_probability
            ai_content=s.ai_content_probability,
            # Execute statement: web_plagiarism=s.web_plagiarism_score
            web_plagiarism=s.web_plagiarism_score,
            # Execute statement: file_url=s.file_url
            file_url=s.file_url,
            # Execute statement: created_at=s.created_at
            created_at=s.created_at,
        # Execute statement: )
        )
        # Execute statement: for s in created_submissions
        for s in created_submissions
    # Execute statement: ]
    ]

    # Return result: BatchUploadResponse(
    return BatchUploadResponse(
        # Execute statement: batch_id=batch_id
        batch_id=batch_id,
        # Execute statement: total_files=len(created_submissions)
        total_files=len(created_submissions),
        # Execute statement: uploaded_files=uploaded_names
        uploaded_files=uploaded_names,
        # Execute statement: submissions=responses
        submissions=responses,
    # Execute statement: )
    )


# Route handler handling HTTP POST requests
@router.post("/assignments/{assignment_id}/submissions/upload", response_model=SubmissionResponse)
# Define asynchronous function to upload single file submission
async def upload_single_file_submission(
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Set file: UploadFile to File(...)
    file: UploadFile = File(...),
    # Set student_name: Optional[str] to Form(None)
    student_name: Optional[str] = Form(None),
    # Set student_roll: Optional[str] to Form(None)
    student_roll: Optional[str] = Form(None),
    # Set student_email: Optional[str] to Form(None)
    student_email: Optional[str] = Form(None),
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
    # Set instructor: Instructor to Depends(get_current_instructor)
    instructor: Instructor = Depends(get_current_instructor),
# Execute statement: )
):
    """Multipart upload for single student document (.docx, .pdf, .txt)."""
    # Set assignment to _ensure_assignment_exists(db, assignment_id)
    assignment = _ensure_assignment_exists(db, assignment_id)
    # Verify condition: not assignment
    if not assignment:
        # Raise error condition: HTTPException(status_code=404, detail="Assignment not found")
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Set content to await file.read()
    content = await file.read()
    # Set upload_dir to os.path.join(os.getcwd(), "uploads", assignment_id)
    upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
    # Execute statement: os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    # Set sub to _create_single_submission(
    sub = _create_single_submission(
        # Execute statement: db=db
        db=db,
        # Execute statement: assignment_id=assignment_id
        assignment_id=assignment_id,
        # Execute statement: filename=file.filename
        filename=file.filename,
        # Execute statement: content=content
        content=content,
        # Execute statement: upload_dir=upload_dir
        upload_dir=upload_dir,
        # Execute statement: custom_name=student_name
        custom_name=student_name,
        # Execute statement: custom_roll=student_roll
        custom_roll=student_roll,
        # Execute statement: custom_email=student_email
        custom_email=student_email,
    # Execute statement: )
    )

    # Begin try block to execute operations safely
    try:
        # Commit transaction modifications to local database
        db.commit()
        # Execute statement: db.refresh(sub)
        db.refresh(sub)
    # Catch and handle exception: except Exception as db_err
    except Exception as db_err:
        # Rollback database transaction on error
        db.rollback()
        # Log error notice message to runtime logger
        logger.error(f"Database error saving submission: {db_err}")
        # Raise error condition: HTTPException(status_code=500, detail="Database error persisting submission")
        raise HTTPException(status_code=500, detail="Database error persisting submission")

    # Sync to Supabase
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Execute statement: supabase.table("submissions").upsert({
        supabase.table("submissions").upsert({
            # Execute statement: "id": sub.id
            "id": sub.id,
            # Execute statement: "assignment_id": sub.assignment_id
            "assignment_id": sub.assignment_id,
            # Execute statement: "student_name_encrypted": sub.student_name_encrypted
            "student_name_encrypted": sub.student_name_encrypted,
            # Execute statement: "student_roll_encrypted": sub.student_roll_encrypted
            "student_roll_encrypted": sub.student_roll_encrypted,
            # Execute statement: "student_email_encrypted": sub.student_email_encrypted
            "student_email_encrypted": sub.student_email_encrypted,
            # Execute statement: "file_name": sub.file_name
            "file_name": sub.file_name,
            # Execute statement: "file_path": sub.file_path
            "file_path": sub.file_path,
            # Execute statement: "file_url": sub.file_url
            "file_url": sub.file_url,
            # Execute statement: "file_type": sub.file_type
            "file_type": sub.file_type,
            # Execute statement: "extracted_text": sub.extracted_text
            "extracted_text": sub.extracted_text,
            # Execute statement: "content": sub.content or sub.extracted_text or ""
            "content": sub.content or sub.extracted_text or "",
            # Execute statement: "file_content": sub.file_content
            "file_content": sub.file_content,
            # Execute statement: "similarity_score": 0.0
            "similarity_score": 0.0,
            # Execute statement: "ai_content_probability": 0.0
            "ai_content_probability": 0.0,
            # Execute statement: "web_plagiarism_score": 0.0
            "web_plagiarism_score": 0.0,
            # Execute statement: "web_sources": []
            "web_sources": [],
            # Execute statement: "status": sub.status
            "status": sub.status,
        # Execute statement: }).execute()
        }).execute()
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase single file upload sync notice: {e}")

    # Return result: SubmissionResponse(
    return SubmissionResponse(
        # Execute statement: id=sub.id
        id=sub.id,
        # Execute statement: assignment_id=sub.assignment_id
        assignment_id=sub.assignment_id,
        # Execute statement: student=sub.student_name
        student=sub.student_name,
        # Execute statement: roll=sub.student_roll
        roll=sub.student_roll,
        # Execute statement: file_name=sub.file_name
        file_name=sub.file_name,
        # Execute statement: status=sub.status
        status=sub.status,
        # Execute statement: score=sub.draft_grade.suggested_score if sub.draft_grade else None
        score=sub.draft_grade.suggested_score if sub.draft_grade else None,
        # Execute statement: similarity=sub.similarity_score
        similarity=sub.similarity_score,
        # Execute statement: ai_content=sub.ai_content_probability
        ai_content=sub.ai_content_probability,
        # Execute statement: web_plagiarism=sub.web_plagiarism_score
        web_plagiarism=sub.web_plagiarism_score,
        # Execute statement: file_url=sub.file_url
        file_url=sub.file_url,
        # Execute statement: created_at=sub.created_at
        created_at=sub.created_at,
    # Execute statement: )
    )


# Route handler handling HTTP POST requests
@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionResponse)
# Define asynchronous function to create single submission
async def create_single_submission(
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Execute statement: request: Request
    request: Request,
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
    # Set instructor: Instructor to Depends(get_current_instructor)
    instructor: Instructor = Depends(get_current_instructor),
# Execute statement: )
):
    """Create a single student submission via multipart file upload (.docx, .pdf, .txt)

    or raw JSON payload with extracted text.
    """
    # Set assignment to _ensure_assignment_exists(db, assignment_id)
    assignment = _ensure_assignment_exists(db, assignment_id)
    # Verify condition: not assignment
    if not assignment:
        # Raise error condition: HTTPException(status_code=404, detail="Assignment not found")
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Set content_type to request.headers.get("content-type", "")
    content_type = request.headers.get("content-type", "")

    # Verify condition: "multipart/form-data" in content_type
    if "multipart/form-data" in content_type:
        # Set form to await request.form()
        form = await request.form()
        # Set uploaded_file to form.get("file")
        uploaded_file = form.get("file")
        # Verify condition: not uploaded_file and "files" in form
        if not uploaded_file and "files" in form:
            # Set uploaded_file to form.get("files")
            uploaded_file = form.get("files")

        # Set student_name to str(form.get("student_name") or "")
        student_name = str(form.get("student_name") or "")
        # Set student_roll to str(form.get("student_roll") or "")
        student_roll = str(form.get("student_roll") or "")
        # Set student_email to str(form.get("student_email") or "")
        student_email = str(form.get("student_email") or "")
        # Set raw_text to str(form.get("extracted_text") or form.get("content") or "")
        raw_text = str(form.get("extracted_text") or form.get("content") or "")

        # Verify condition: uploaded_file and hasattr(uploaded_file, "read")
        if uploaded_file and hasattr(uploaded_file, "read"):
            # Set filename to uploaded_file.filename
            filename = uploaded_file.filename
            # Set content_bytes to await uploaded_file.read()
            content_bytes = await uploaded_file.read()
            # Set upload_dir to os.path.join(os.getcwd(), "uploads", assignment_id)
            upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
            # Execute statement: os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(upload_dir, exist_ok=True)
            # Set sub to _create_single_submission(
            sub = _create_single_submission(
                # Execute statement: db
                db,
                # Execute statement: assignment_id
                assignment_id,
                # Execute statement: filename
                filename,
                # Execute statement: content_bytes
                content_bytes,
                # Execute statement: upload_dir
                upload_dir,
                # Execute statement: custom_name=student_name
                custom_name=student_name,
                # Execute statement: custom_roll=student_roll
                custom_roll=student_roll,
                # Execute statement: custom_email=student_email
                custom_email=student_email,
            # Execute statement: )
            )
        # Handle alternative fallback path
        else:
            # Check duplicate submission text
            text_to_check = (raw_text or "").strip()
            if text_to_check and len(text_to_check) > 30:
                existing_dups = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
                for es in existing_dups:
                    if (es.extracted_text and es.extracted_text.strip() == text_to_check) or (es.content and es.content.strip() == text_to_check):
                        raise HTTPException(
                            status_code=400,
                            detail="Duplicate upload: An identical submission text already exists for this assignment."
                        )

            # Set sub_id to f"sub_{uuid.uuid4().hex[:8]}"
            sub_id = f"sub_{uuid.uuid4().hex[:8]}"
            # Set sub to Submission(
            sub = Submission(
                # Execute statement: id=sub_id
                id=sub_id,
                # Execute statement: assignment_id=assignment_id
                assignment_id=assignment_id,
                # Execute statement: file_name=f"{student_name.lower().replace(' ', '_') or 'manual'}_submission.txt"
                file_name=f"{student_name.lower().replace(' ', '_') or 'manual'}_submission.txt",
                # Execute statement: file_path=""
                file_path="",
                # Execute statement: file_url=None
                file_url=None,
                # Execute statement: file_type="text"
                file_type="text",
                # Execute statement: extracted_text=raw_text
                extracted_text=raw_text,
                # Execute statement: content=raw_text
                content=raw_text,
                # Execute statement: file_content=raw_text
                file_content=raw_text,
                # Execute statement: status="pending"
                status="pending",
            # Execute statement: )
            )
            # Set sub.student_name to student_name or "Anonymous Student"
            sub.student_name = student_name or "Anonymous Student"
            # Set sub.student_roll to student_roll or f"2024-{uuid.uuid4().hex[:4]}"
            sub.student_roll = student_roll or f"2024-{uuid.uuid4().hex[:4]}"
            # Set sub.student_email to student_email or f"{sub.student_name.lower().replace(' ', '.')}@university.edu"
            sub.student_email = student_email or f"{sub.student_name.lower().replace(' ', '.')}@university.edu"
            # Add entity record to database session
            db.add(sub)
    # Handle alternative fallback path
    else:
        # Standard JSON body
        try:
            # Set body to await request.json()
            body = await request.json()
            # Set payload to SubmissionCreate(**body)
            payload = SubmissionCreate(**body)
        # Catch and handle exception: except Exception as parse_err
        except Exception as parse_err:
            # Log error notice message to runtime logger
            logger.error(f"Failed to parse submission JSON: {parse_err}")
            # Raise error condition: HTTPException(status_code=422, detail="Invalid submission payload format")
            raise HTTPException(status_code=422, detail="Invalid submission payload format")

        # Check duplicate submission text
        text_to_check = (payload.extracted_text or "").strip()
        if text_to_check and len(text_to_check) > 30:
            existing_dups = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
            for es in existing_dups:
                if (es.extracted_text and es.extracted_text.strip() == text_to_check) or (es.content and es.content.strip() == text_to_check):
                    raise HTTPException(
                        status_code=400,
                        detail="Duplicate upload: An identical submission text already exists for this assignment."
                    )

        # Set sub_id to f"sub_{uuid.uuid4().hex[:8]}"
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        # Set sub to Submission(
        sub = Submission(
            # Execute statement: id=sub_id
            id=sub_id,
            # Execute statement: assignment_id=assignment_id
            assignment_id=assignment_id,
            # Execute statement: file_name=f"{payload.student_name.lower().replace(' ', '_')}_submission.txt"
            file_name=f"{payload.student_name.lower().replace(' ', '_')}_submission.txt",
            # Execute statement: file_path=""
            file_path="",
            # Execute statement: file_url=None
            file_url=None,
            # Execute statement: file_type="text"
            file_type="text",
            # Execute statement: extracted_text=payload.extracted_text or ""
            extracted_text=payload.extracted_text or "",
            # Execute statement: content=payload.extracted_text or ""
            content=payload.extracted_text or "",
            # Execute statement: file_content=payload.extracted_text or ""
            file_content=payload.extracted_text or "",
            # Execute statement: status="pending"
            status="pending",
        # Execute statement: )
        )
        # Set sub.student_name to payload.student_name
        sub.student_name = payload.student_name
        # Set sub.student_roll to payload.student_roll
        sub.student_roll = payload.student_roll
        # Set sub.student_email to payload.student_email or f"{payload.student_name.lower().replace(' ', '.')}@university.edu"
        sub.student_email = payload.student_email or f"{payload.student_name.lower().replace(' ', '.')}@university.edu"
        # Add entity record to database session
        db.add(sub)

    # Begin try block to execute operations safely
    try:
        # Commit transaction modifications to local database
        db.commit()
        # Execute statement: db.refresh(sub)
        db.refresh(sub)
    # Catch and handle exception: except Exception as db_err
    except Exception as db_err:
        # Rollback database transaction on error
        db.rollback()
        # Log error notice message to runtime logger
        logger.error(f"Database commit error for submission: {db_err}")
        # Raise error condition: HTTPException(status_code=500, detail="Database error persisting submission")
        raise HTTPException(status_code=500, detail="Database error persisting submission")

    # Sync to Supabase
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Execute statement: supabase.table("submissions").upsert({
        supabase.table("submissions").upsert({
            # Execute statement: "id": sub.id
            "id": sub.id,
            # Execute statement: "assignment_id": sub.assignment_id
            "assignment_id": sub.assignment_id,
            # Execute statement: "student_name_encrypted": sub.student_name_encrypted
            "student_name_encrypted": sub.student_name_encrypted,
            # Execute statement: "student_roll_encrypted": sub.student_roll_encrypted
            "student_roll_encrypted": sub.student_roll_encrypted,
            # Execute statement: "student_email_encrypted": sub.student_email_encrypted
            "student_email_encrypted": sub.student_email_encrypted,
            # Execute statement: "file_name": sub.file_name
            "file_name": sub.file_name,
            # Execute statement: "file_path": sub.file_path
            "file_path": sub.file_path,
            # Execute statement: "file_url": sub.file_url
            "file_url": sub.file_url,
            # Execute statement: "file_type": sub.file_type
            "file_type": sub.file_type,
            # Execute statement: "extracted_text": sub.extracted_text
            "extracted_text": sub.extracted_text,
            # Execute statement: "content": sub.content or sub.extracted_text or ""
            "content": sub.content or sub.extracted_text or "",
            # Execute statement: "file_content": sub.file_content
            "file_content": sub.file_content,
            # Execute statement: "similarity_score": 0.0
            "similarity_score": 0.0,
            # Execute statement: "ai_content_probability": 0.0
            "ai_content_probability": 0.0,
            # Execute statement: "web_plagiarism_score": 0.0
            "web_plagiarism_score": 0.0,
            # Execute statement: "web_sources": []
            "web_sources": [],
            # Execute statement: "status": "pending"
            "status": "pending",
        # Execute statement: }).execute()
        }).execute()
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Supabase single submission sync notice: {e}")

    # Record structured audit log event for compliance
    log_audit_event(
        # Execute statement: actor=instructor.name
        actor=instructor.name,
        # Execute statement: action="CREATE_SUBMISSION"
        action="CREATE_SUBMISSION",
        # Execute statement: entity="Submission"
        entity="Submission",
        # Execute statement: entity_id=sub.id
        entity_id=sub.id,
        # Execute statement: details=f"Submission entered for {sub.student_name} ({sub.student_roll})"
        details=f"Submission entered for {sub.student_name} ({sub.student_roll})",
    # Execute statement: )
    )

    # Return result: SubmissionResponse(
    return SubmissionResponse(
        # Execute statement: id=sub.id
        id=sub.id,
        # Execute statement: assignment_id=sub.assignment_id
        assignment_id=sub.assignment_id,
        # Execute statement: student=sub.student_name
        student=sub.student_name,
        # Execute statement: roll=sub.student_roll
        roll=sub.student_roll,
        # Execute statement: file_name=sub.file_name
        file_name=sub.file_name,
        # Execute statement: status=sub.status
        status=sub.status,
        # Execute statement: score=0.0
        score=0.0,
        # Execute statement: similarity=0.0
        similarity=0.0,
        # Execute statement: ai_content=0.0
        ai_content=0.0,
        # Execute statement: web_plagiarism=0.0
        web_plagiarism=0.0,
        # Execute statement: file_url=sub.file_url
        file_url=sub.file_url,
        # Execute statement: created_at=sub.created_at
        created_at=sub.created_at,
    # Execute statement: )
    )


# Route handler handling HTTP GET requests
@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionResponse])
# Define function to get assignment submissions
def get_assignment_submissions(
    # Execute statement: assignment_id: str
    assignment_id: str,
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
# Execute statement: )
):
    """Retrieve all submissions for an assignment with decrypted student names,

    file URLs, and plagiarism scores.
    """
    # Set submissions to db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    # Verify condition: not submissions
    if not submissions:
        # Check Supabase database
        try:
            # Import supabase from app.core.supabase
            from app.core.supabase import supabase
            # Set res to supabase.table("submissions").select("*").eq("assignment_id", assignment_id).execute()
            res = supabase.table("submissions").select("*").eq("assignment_id", assignment_id).execute()
            # Verify condition: res.data
            if res.data:
                # Iterate through: row in res.data
                for row in res.data:
                    # Set existing to db.query(Submission).filter(Submission.id == row["id"]).first()
                    existing = db.query(Submission).filter(Submission.id == row["id"]).first()
                    # Verify condition: not existing
                    if not existing:
                        # Set s to Submission(
                        s = Submission(
                            # Execute statement: id=row["id"]
                            id=row["id"],
                            # Execute statement: assignment_id=row["assignment_id"]
                            assignment_id=row["assignment_id"],
                            # Execute statement: student_name_encrypted=row["student_name_encrypted"]
                            student_name_encrypted=row["student_name_encrypted"],
                            # Execute statement: student_roll_encrypted=row["student_roll_encrypted"]
                            student_roll_encrypted=row["student_roll_encrypted"],
                            # Execute statement: student_email_encrypted=row.get("student_email_encrypted")
                            student_email_encrypted=row.get("student_email_encrypted"),
                            # Execute statement: file_name=row["file_name"]
                            file_name=row["file_name"],
                            # Execute statement: file_path=row.get("file_path", "")
                            file_path=row.get("file_path", ""),
                            # Execute statement: file_url=row.get("file_url")
                            file_url=row.get("file_url"),
                            # Execute statement: file_type=row.get("file_type", "pdf")
                            file_type=row.get("file_type", "pdf"),
                            # Execute statement: extracted_text=row.get("extracted_text")
                            extracted_text=row.get("extracted_text"),
                            # Execute statement: content=row.get("content") or row.get("extracted_text") or ""
                            content=row.get("content") or row.get("extracted_text") or "",
                            # Execute statement: file_content=row.get("file_content")
                            file_content=row.get("file_content"),
                            # Execute statement: similarity_score=float(row.get("similarity_score") or 0.0)
                            similarity_score=float(row.get("similarity_score") or 0.0),
                            # Execute statement: ai_content_probability=float(row.get("ai_content_probability") or 0.0)
                            ai_content_probability=float(row.get("ai_content_probability") or 0.0),
                            # Execute statement: web_plagiarism_score=float(row.get("web_plagiarism_score") or 0.0)
                            web_plagiarism_score=float(row.get("web_plagiarism_score") or 0.0),
                            # Execute statement: status=row.get("status", "pending")
                            status=row.get("status", "pending"),
                        # Execute statement: )
                        )
                        # Add entity record to database session
                        db.add(s)
                # Commit transaction modifications to local database
                db.commit()
                # Set submissions to db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
                submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
        # Catch and handle exception: except Exception as e
        except Exception as e:
            # Log warning notice message to runtime logger
            logger.warning(f"Supabase submissions fetch fallback notice: {e}")

    # Set res_list to []
    res_list = []
    # Iterate through: s in submissions
    for s in submissions:
        # Score defaults to None when submission has not yet been evaluated by educator command
        score = None
        max_s = None
        crit = None
        fb = None
        plag = None
        if s.draft_grade:
            score = (
                s.draft_grade.final_score
                if s.draft_grade.final_score is not None
                else (
                    s.draft_grade.total_score
                    if s.draft_grade.total_score is not None
                    else s.draft_grade.suggested_score
                )
            )
            max_s = s.draft_grade.max_score or 100.0
            crit = s.draft_grade.criteria_breakdown or s.draft_grade.criteria_scores
            fb = s.draft_grade.feedback or s.draft_grade.ai_feedback
            plag = s.draft_grade.plagiarism_report
        elif s.status in ("completed", "graded", "evaluated"):
            draft = db.query(DraftGrade).filter(DraftGrade.submission_id == s.id).first()
            if draft:
                score = (
                    draft.final_score
                    if draft.final_score is not None
                    else (
                        draft.total_score
                        if draft.total_score is not None
                        else draft.suggested_score
                    )
                )
                max_s = draft.max_score or 100.0
                crit = draft.criteria_breakdown or draft.criteria_scores
                fb = draft.feedback or draft.ai_feedback
                plag = draft.plagiarism_report

        # If status indicates review required or failure or not yet evaluated, score is strictly None
        if s.status in ("needs_review", "grading_failed", "unmatched", "ready", "queued"):
            score = None

        # Preserve student full name and ensure it never renders as single letter "A"
        display_student = s.student_name
        if not display_student or len(display_student.strip()) <= 1 or display_student.strip().upper() in ("A", "UNMATCHED"):
            display_student = s.file_name or "Submission"

        res_list.append(
            SubmissionResponse(
                id=s.id,
                assignment_id=s.assignment_id,
                student=display_student,
                roll=s.student_roll,
                student_id=s.student_id,
                file_name=s.file_name,
                status=s.status,
                score=score,
                max_score=max_s,
                similarity=s.similarity_score,
                ai_content=s.ai_content_probability,
                web_plagiarism=s.web_plagiarism_score,
                file_url=s.file_url,
                criteria_scores=crit,
                is_unmatched=bool(not s.student_id or s.student_roll == "UNMATCHED"),
                feedback=fb,
                plagiarism_report=plag,
                created_at=s.created_at,
            )
        )
    # Return result: res_list
    return res_list


# Route handler to re-grade a single submission
@router.post("/submissions/{submission_id}/re-grade")
@router.post("/submissions/{submission_id}/regrade")
def regrade_submission_direct(
    submission_id: str,
    db: Session = Depends(get_db),
):
    """Re-runs grading for a single submission using Phase 5 autograding prompt and strict arithmetic."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    from app.workers.evaluation_tasks import run_evaluation_batch_logic
    result = run_evaluation_batch_logic(
        job_id=f"regrade_{submission_id[:8]}",
        assignment_id=sub.assignment_id,
        submission_ids=[submission_id],
    )
    return {"status": "completed", "submission_id": submission_id, "result": result}


# Route handler to retrieve all submissions optionally filtered by assignment_id
@router.get("/submissions", response_model=List[SubmissionResponse])
def list_all_submissions(
    assignment_id: Optional[str] = Query(None, description="Optional assignment ID filter"),
    db: Session = Depends(get_db),
):
    """Retrieve all submissions, optionally filtered by assignment_id query parameter."""
    if assignment_id:
        return get_assignment_submissions(assignment_id=assignment_id, db=db)
    all_subs = db.query(Submission).all()
    if not all_subs:
        return []
    res_list = []
    for s in all_subs:
        display_name = s.student_name
        if not display_name or len(display_name.strip()) <= 1 or display_name.strip().upper() in ("A", "UNMATCHED"):
            display_name = s.file_name or "Submission"
        res_list.append(SubmissionResponse(
            id=s.id,
            assignment_id=s.assignment_id,
            student=display_name,
            roll=s.student_roll,
            file_name=s.file_name,
            file_type=s.file_type or "txt",
            status=s.status,
            created_at=s.created_at,
        ))
    return res_list


# Route handler handling HTTP PATCH requests
@router.patch("/submissions/{submission_id}/assign-student", response_model=SubmissionResponse)
# Define function to assign submission student
def assign_submission_student(
    # Execute statement: submission_id: str
    submission_id: str,
    # Execute statement: payload: AssignStudentRequest
    payload: AssignStudentRequest,
    # Set db: Session to Depends(get_db)
    db: Session = Depends(get_db),
# Execute statement: )
):
    """Manually assign an unmatched submission to an enrolled student."""
    # Set sub to db.query(Submission).filter(Submission.id == submission_id).first()
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # Verify condition: not sub
    if not sub:
        # Raise error condition: HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(status_code=404, detail="Submission not found")

    # Set student_record to None
    student_record = None
    # Begin try block to execute operations safely
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Set s_res to supabase.table("students").select("*").eq("id", payload.student_id).execute()
        s_res = supabase.table("students").select("*").eq("id", payload.student_id).execute()
        # Verify condition: s_res.data
        if s_res.data:
            # Set student_record to s_res.data[0]
            student_record = s_res.data[0]
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Error fetching student from Supabase: {e}")

    # Set student_name to student_record.get("full_name") if student_record else "Assigned Student"
    student_name = student_record.get("full_name") if student_record else "Assigned Student"
    # Set student_roll to student_record.get("roll_number") if student_record else "UNKNOWN"
    student_roll = student_record.get("roll_number") if student_record else "UNKNOWN"
    # Set student_email to student_record.get("email") if student_record else f"{student_roll}@university.edu"
    student_email = student_record.get("email") if student_record else f"{student_roll}@university.edu"

    # Set sub.student_id to payload.student_id
    sub.student_id = payload.student_id
    # Set sub.student_name to student_name
    sub.student_name = student_name
    # Set sub.student_roll to student_roll
    sub.student_roll = student_roll
    # Set sub.student_email to student_email
    sub.student_email = student_email
    # Verify condition: sub.status == "unmatched"
    if sub.status == "unmatched":
        # Set sub.status to "queued"
        sub.status = "queued"

    # Commit transaction modifications to local database
    db.commit()
    # Execute statement: db.refresh(sub)
    db.refresh(sub)

    # Sync to Supabase
    try:
        # Import supabase from app.core.supabase
        from app.core.supabase import supabase
        # Execute statement: supabase.table("submissions").update({
        supabase.table("submissions").update({
            # Execute statement: "student_id": payload.student_id
            "student_id": payload.student_id,
            # Execute statement: "status": sub.status
            "status": sub.status,
            # Execute statement: "student_name_encrypted": sub.student_name_encrypted
            "student_name_encrypted": sub.student_name_encrypted,
            # Execute statement: "student_roll_encrypted": sub.student_roll_encrypted
            "student_roll_encrypted": sub.student_roll_encrypted,
        # Execute statement: }).eq("id", submission_id).execute()
        }).eq("id", submission_id).execute()
    # Catch and handle exception: except Exception as e
    except Exception as e:
        # Log warning notice message to runtime logger
        logger.warning(f"Error updating submission in Supabase: {e}")

    # Score defaults to None when submission is ungraded
    score = None
    # Max score defaults to None when submission is ungraded
    max_s = None
    # Criteria breakdown defaults to None
    crit = None
    # Qualitative feedback defaults to None
    fb = None
    # Plagiarism report defaults to None
    plag = None
    # Verify condition: sub.draft_grade
    if sub.draft_grade:
        # Set score to (
        score = (
            # Execute statement: sub.draft_grade.final_score
            sub.draft_grade.final_score
            # Execute statement: if sub.draft_grade.final_score is not None
            if sub.draft_grade.final_score is not None
            # Execute statement: else (
            else (
                # Execute statement: sub.draft_grade.total_score
                sub.draft_grade.total_score
                # Execute statement: if sub.draft_grade.total_score is not None
                if sub.draft_grade.total_score is not None
                # Execute statement: else (sub.draft_grade.suggested_score or 0.0)
                else (sub.draft_grade.suggested_score or 0.0)
            # Execute statement: )
            )
        # Execute statement: )
        )
        # Set max_s to sub.draft_grade.max_score or 100.0
        max_s = sub.draft_grade.max_score or 100.0
        # Set crit to sub.draft_grade.criteria_breakdown or sub.draft_grade.criteria_scores
        crit = sub.draft_grade.criteria_breakdown or sub.draft_grade.criteria_scores
        # Set fb to sub.draft_grade.feedback or sub.draft_grade.ai_feedback
        fb = sub.draft_grade.feedback or sub.draft_grade.ai_feedback
        # Set plag to sub.draft_grade.plagiarism_report
        plag = sub.draft_grade.plagiarism_report

    # Return result: SubmissionResponse(
    return SubmissionResponse(
        # Execute statement: id=sub.id
        id=sub.id,
        # Execute statement: assignment_id=sub.assignment_id
        assignment_id=sub.assignment_id,
        # Execute statement: student=sub.student_name
        student=sub.student_name,
        # Execute statement: roll=sub.student_roll
        roll=sub.student_roll,
        # Execute statement: student_id=sub.student_id
        student_id=sub.student_id,
        # Execute statement: file_name=sub.file_name
        file_name=sub.file_name,
        # Execute statement: status=sub.status
        status=sub.status,
        # Execute statement: score=score
        score=score,
        # Execute statement: max_score=max_s
        max_score=max_s,
        # Execute statement: similarity=sub.similarity_score or 0.0
        similarity=sub.similarity_score or 0.0,
        # AI content probability, None until evaluation has run
        ai_content=sub.ai_content_probability if sub.draft_grade else None,
        # Web search plagiarism score, None until checked
        web_plagiarism=sub.web_plagiarism_score if sub.draft_grade else None,
        # Execute statement: file_url=sub.file_url
        file_url=sub.file_url,
        # Execute statement: criteria_scores=crit
        criteria_scores=crit,
        # Execute statement: feedback=fb
        feedback=fb,
        # Execute statement: plagiarism_report=plag
        plagiarism_report=plag,
        # Execute statement: created_at=sub.created_at
        created_at=sub.created_at,
    # Execute statement: )
    )


# Route handler handling HTTP DELETE requests
@router.delete("/submissions/{submission_id}", status_code=204)
def delete_single_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    current_instructor: Optional[Instructor] = Depends(get_current_instructor),
):
    """Delete a single student submission and cleanly cascade associated similarity matches."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # Idempotent deletion: if submission is already removed or does not exist, return 204
    if not sub:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Validate instructor ownership if assignment/course is found
    assign = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    if assign:
        course = db.query(Course).filter(Course.id == assign.course_id).first()
        if (
            course
            and course.instructor_id
            and current_instructor
            and current_instructor.id
            and course.instructor_id != current_instructor.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete submissions for this course.",
            )

    try:
        # Cascade clean up similarity matches referencing this submission
        db.query(SimilarityMatch).filter(
            (SimilarityMatch.submission_a_id == submission_id) |
            (SimilarityMatch.submission_b_id == submission_id)
        ).delete(synchronize_session=False)

        # Cascade clean up draft grades
        db.query(DraftGrade).filter(DraftGrade.submission_id == submission_id).delete(synchronize_session=False)

        # Delete submission entity record from database session
        db.delete(sub)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Error deleting submission {submission_id} from local db: {db_err}")
        raise HTTPException(status_code=500, detail="Failed to delete submission.")

    if settings.USE_SUPABASE:
        try:
            from app.core.supabase import supabase
            supabase.table("submissions").delete().eq("id", submission_id).execute()
        except Exception as e:
            logger.warning(f"Supabase submission delete notice: {e}")

    return None


# Route handler handling HTTP DELETE requests
@router.delete("/assignments/{assignment_id}/submissions", status_code=200)
def clear_assignment_submissions(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_instructor: Optional[Instructor] = Depends(get_current_instructor),
):
    """Clear all submissions for an assignment to allow clean input."""
    # Verify assignment exists
    assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if assign:
        course = db.query(Course).filter(Course.id == assign.course_id).first()
        if (
            course
            and course.instructor_id
            and current_instructor
            and current_instructor.id
            and course.instructor_id != current_instructor.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to clear submissions for this course.",
            )

    subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    count = len(subs)
    try:
        # Clean up all similarity matches for this assignment
        db.query(SimilarityMatch).filter(SimilarityMatch.assignment_id == assignment_id).delete(synchronize_session=False)

        # Clean up draft grades for these submissions
        sub_ids = [s.id for s in subs]
        if sub_ids:
            db.query(DraftGrade).filter(DraftGrade.submission_id.in_(sub_ids)).delete(synchronize_session=False)

        for s in subs:
            db.delete(s)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Error clearing submissions from local db: {db_err}")
        raise HTTPException(status_code=500, detail="Failed to clear submissions.")

    if settings.USE_SUPABASE:
        try:
            from app.core.supabase import supabase
            supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
        except Exception as e:
            logger.warning(f"Supabase clear submissions notice: {e}")

    return {"cleared": count}
