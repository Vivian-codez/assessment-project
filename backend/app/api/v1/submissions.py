"""Submission, File Ingestion, and Batch Upload API endpoints.

Handles:
- Word document (.docx) extraction via python-docx with XML fallback
- Multi-format ingestion (.pdf, .txt, .docx, code, .zip archives)
- Raw file persistence into Supabase Storage bucket 'submissions' with public URL generation
- Text storage in database under extracted_text and content
- FERPA encryption on student identifiers
"""

import os
import uuid
import zipfile
from io import BytesIO
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger, log_audit_event
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate, SubmissionResponse, BatchUploadResponse
from app.services.pdf_service import pdf_service
from app.services.supabase_service import supabase_service
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(tags=["Submissions"])


def _ensure_assignment_exists(db: Session, assignment_id: str) -> Optional[Assignment]:
    """Ensure assignment exists in local DB, checking and replicating from Supabase if needed."""
    try:
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if assignment:
            return assignment

        from app.core.supabase import supabase
        from app.models.course import Course
        res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        if res.data:
            a_data = res.data[0]
            course_id = a_data["course_id"]
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                c_res = supabase.table("courses").select("*").eq("id", course_id).execute()
                if c_res.data:
                    c_data = c_res.data[0]
                    course = Course(
                        id=c_data["id"],
                        name=c_data["name"],
                        code=c_data["code"],
                        section=c_data.get("section", "A"),
                        tone=c_data.get("tone", "lav"),
                        students_count=c_data.get("students_count", 0),
                        instructor_id=c_data.get("instructor_id"),
                    )
                    db.add(course)
                    db.commit()
            assignment = Assignment(
                id=a_data["id"],
                course_id=course_id,
                title=a_data["title"],
                description=a_data.get("description"),
                max_score=float(a_data.get("max_score", 100.0)),
                rubric_id=a_data.get("rubric_id"),
                reference_assignment_text=a_data.get("reference_assignment_text"),
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            return assignment
    except Exception as e:
        logger.warning(f"Supabase assignment lookup fallback notice: {e}")

    return None


def _create_single_submission(
    db: Session,
    assignment_id: str,
    filename: str,
    content: bytes,
    upload_dir: str,
    custom_name: Optional[str] = None,
    custom_roll: Optional[str] = None,
    custom_email: Optional[str] = None,
) -> Submission:
    """Helper to extract text with python-docx/pdf_service, upload raw file to Supabase Storage,

    and persist with FERPA encryption.
    """
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as write_err:
        logger.warning(f"Local file write notice for {filename}: {write_err}")
        file_path = ""

    # 1. Upload raw file to Supabase Storage bucket 'submissions' and obtain file_url
    file_url = None
    try:
        file_url = supabase_service.upload_file_to_storage(
            file_bytes=content,
            file_name=filename,
            assignment_id=assignment_id,
        )
    except Exception as storage_err:
        logger.warning(f"Supabase Storage persistence error for {filename}: {storage_err}")

    # 2. Determine file type and format file content string
    ext = filename.lower().split(".")[-1] if "." in filename else "text"
    is_binary = ext in {"pdf", "docx", "doc", "zip", "png", "jpg", "jpeg", "tar", "gz"}

    import base64
    if not is_binary:
        try:
            file_content_str = content.decode("utf-8", errors="replace")
        except Exception:
            file_content_str = base64.b64encode(content).decode("ascii")
    else:
        file_content_str = base64.b64encode(content).decode("ascii")

    # 3. Clean document extraction (python-docx for .docx, pdf_service for .pdf/.txt)
    extracted_text = pdf_service.extract_text_from_bytes(content, filename)
    if not extracted_text and not is_binary:
        extracted_text = file_content_str

    # 4. Student metadata parsing
    if custom_name and custom_name.strip():
        student_name = custom_name.strip()
    else:
        clean_stem = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
        parts = clean_stem.split()
        if len(parts) >= 2:
            student_name = f"{parts[1].capitalize()} {parts[0].capitalize()}"
        else:
            student_name = clean_stem.capitalize() or "Anonymous Student"

    import random
    roll = custom_roll.strip() if (custom_roll and custom_roll.strip()) else f"2024-{random.randint(10, 99):03d}"
    email = custom_email.strip() if (custom_email and custom_email.strip()) else f"{student_name.lower().replace(' ', '.')}@university.edu"

    sub = Submission(
        id=f"sub_{uuid.uuid4().hex[:8]}",
        assignment_id=assignment_id,
        file_name=filename,
        file_path=file_path,
        file_url=file_url,
        file_type=ext,
        extracted_text=extracted_text,
        content=extracted_text or file_content_str,
        file_content=file_content_str,
        status="pending",
    )
    # Uses FERPA transparent encryption setters
    sub.student_name = student_name
    sub.student_roll = roll
    sub.student_email = email

    db.add(sub)
    return sub


@router.post("/assignments/{assignment_id}/submissions/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_submissions(
    assignment_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Batch upload student submissions (.docx, .pdf, .txt, code, and .zip archives).

    Extracts text using python-docx and pdf_service, saves raw files to Supabase Storage,
    and synchronizes records to the Supabase database.
    """
    assignment = _ensure_assignment_exists(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    uploaded_names = []
    created_submissions = []

    upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        filename = file.filename
        content = await file.read()

        # Handle zip bundle extraction
        if filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(content)) as zf:
                    for zip_info in zf.infolist():
                        if not zip_info.is_dir() and not zip_info.filename.startswith("__MACOSX"):
                            extracted_bytes = zf.read(zip_info.filename)
                            inner_name = os.path.basename(zip_info.filename)
                            sub = _create_single_submission(
                                db, assignment_id, inner_name, extracted_bytes, upload_dir
                            )
                            uploaded_names.append(inner_name)
                            created_submissions.append(sub)
            except Exception as e:
                logger.error(f"Error extracting zip archive {filename}: {e}")
                continue
        else:
            sub = _create_single_submission(db, assignment_id, filename, content, upload_dir)
            uploaded_names.append(filename)
            created_submissions.append(sub)

    try:
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database commit error in batch upload: {db_err}")
        raise HTTPException(status_code=500, detail="Database persistence error during batch upload")

    # Sync created submissions to Supabase database (storage & tables)
    try:
        from app.core.supabase import supabase
        supabase_records = [
            {
                "id": s.id,
                "assignment_id": s.assignment_id,
                "student_name_encrypted": s.student_name_encrypted,
                "student_roll_encrypted": s.student_roll_encrypted,
                "student_email_encrypted": s.student_email_encrypted,
                "file_name": s.file_name,
                "file_path": s.file_path,
                "file_url": s.file_url,
                "file_type": s.file_type,
                "extracted_text": s.extracted_text,
                "content": s.content or s.extracted_text or "",
                "file_content": s.file_content,
                "similarity_score": 0.0,
                "ai_content_probability": 0.0,
                "web_plagiarism_score": 0.0,
                "web_sources": [],
                "status": s.status,
            }
            for s in created_submissions
        ]
        if supabase_records:
            supabase.table("submissions").upsert(supabase_records).execute()
            logger.info(f"Synchronized {len(supabase_records)} submissions with Supabase database.")
    except Exception as e:
        logger.warning(f"Supabase batch submission sync notice: {e}")

    log_audit_event(
        actor=instructor.name,
        action="BATCH_UPLOAD",
        entity="Assignment",
        entity_id=assignment_id,
        details=f"Uploaded {len(created_submissions)} files in batch {batch_id}",
    )

    responses = [
        SubmissionResponse(
            id=s.id,
            assignment_id=s.assignment_id,
            student=s.student_name,
            roll=s.student_roll,
            file_name=s.file_name,
            status=s.status,
            score=s.draft_grade.suggested_score if s.draft_grade else 0.0,
            similarity=s.similarity_score,
            ai_content=s.ai_content_probability,
            web_plagiarism=s.web_plagiarism_score,
            file_url=s.file_url,
            created_at=s.created_at,
        )
        for s in created_submissions
    ]

    return BatchUploadResponse(
        batch_id=batch_id,
        total_files=len(created_submissions),
        uploaded_files=uploaded_names,
        submissions=responses,
    )


@router.post("/assignments/{assignment_id}/submissions/upload", response_model=SubmissionResponse)
async def upload_single_file_submission(
    assignment_id: str,
    file: UploadFile = File(...),
    student_name: Optional[str] = Form(None),
    student_roll: Optional[str] = Form(None),
    student_email: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Multipart upload for single student document (.docx, .pdf, .txt)."""
    assignment = _ensure_assignment_exists(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    content = await file.read()
    upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
    os.makedirs(upload_dir, exist_ok=True)

    sub = _create_single_submission(
        db=db,
        assignment_id=assignment_id,
        filename=file.filename,
        content=content,
        upload_dir=upload_dir,
        custom_name=student_name,
        custom_roll=student_roll,
        custom_email=student_email,
    )

    try:
        db.commit()
        db.refresh(sub)
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error saving submission: {db_err}")
        raise HTTPException(status_code=500, detail="Database error persisting submission")

    # Sync to Supabase
    try:
        from app.core.supabase import supabase
        supabase.table("submissions").upsert({
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "student_name_encrypted": sub.student_name_encrypted,
            "student_roll_encrypted": sub.student_roll_encrypted,
            "student_email_encrypted": sub.student_email_encrypted,
            "file_name": sub.file_name,
            "file_path": sub.file_path,
            "file_url": sub.file_url,
            "file_type": sub.file_type,
            "extracted_text": sub.extracted_text,
            "content": sub.content or sub.extracted_text or "",
            "file_content": sub.file_content,
            "similarity_score": 0.0,
            "ai_content_probability": 0.0,
            "web_plagiarism_score": 0.0,
            "web_sources": [],
            "status": "pending",
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase single file upload sync notice: {e}")

    return SubmissionResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student=sub.student_name,
        roll=sub.student_roll,
        file_name=sub.file_name,
        status=sub.status,
        score=0.0,
        similarity=0.0,
        ai_content=0.0,
        web_plagiarism=0.0,
        file_url=sub.file_url,
        created_at=sub.created_at,
    )


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionResponse)
async def create_single_submission(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Create a single student submission via multipart file upload (.docx, .pdf, .txt)

    or raw JSON payload with extracted text.
    """
    assignment = _ensure_assignment_exists(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file and "files" in form:
            uploaded_file = form.get("files")

        student_name = str(form.get("student_name") or "")
        student_roll = str(form.get("student_roll") or "")
        student_email = str(form.get("student_email") or "")
        raw_text = str(form.get("extracted_text") or form.get("content") or "")

        if uploaded_file and hasattr(uploaded_file, "read"):
            filename = uploaded_file.filename
            content_bytes = await uploaded_file.read()
            upload_dir = os.path.join(os.getcwd(), "uploads", assignment_id)
            os.makedirs(upload_dir, exist_ok=True)
            sub = _create_single_submission(
                db,
                assignment_id,
                filename,
                content_bytes,
                upload_dir,
                custom_name=student_name,
                custom_roll=student_roll,
                custom_email=student_email,
            )
        else:
            sub_id = f"sub_{uuid.uuid4().hex[:8]}"
            sub = Submission(
                id=sub_id,
                assignment_id=assignment_id,
                file_name=f"{student_name.lower().replace(' ', '_') or 'manual'}_submission.txt",
                file_path="",
                file_url=None,
                file_type="text",
                extracted_text=raw_text,
                content=raw_text,
                file_content=raw_text,
                status="pending",
            )
            sub.student_name = student_name or "Anonymous Student"
            sub.student_roll = student_roll or f"2024-{uuid.uuid4().hex[:4]}"
            sub.student_email = student_email or f"{sub.student_name.lower().replace(' ', '.')}@university.edu"
            db.add(sub)
    else:
        # Standard JSON body
        try:
            body = await request.json()
            payload = SubmissionCreate(**body)
        except Exception as parse_err:
            logger.error(f"Failed to parse submission JSON: {parse_err}")
            raise HTTPException(status_code=422, detail="Invalid submission payload format")

        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        sub = Submission(
            id=sub_id,
            assignment_id=assignment_id,
            file_name=f"{payload.student_name.lower().replace(' ', '_')}_submission.txt",
            file_path="",
            file_url=None,
            file_type="text",
            extracted_text=payload.extracted_text or "",
            content=payload.extracted_text or "",
            file_content=payload.extracted_text or "",
            status="pending",
        )
        sub.student_name = payload.student_name
        sub.student_roll = payload.student_roll
        sub.student_email = payload.student_email or f"{payload.student_name.lower().replace(' ', '.')}@university.edu"
        db.add(sub)

    try:
        db.commit()
        db.refresh(sub)
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database commit error for submission: {db_err}")
        raise HTTPException(status_code=500, detail="Database error persisting submission")

    # Sync to Supabase
    try:
        from app.core.supabase import supabase
        supabase.table("submissions").upsert({
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "student_name_encrypted": sub.student_name_encrypted,
            "student_roll_encrypted": sub.student_roll_encrypted,
            "student_email_encrypted": sub.student_email_encrypted,
            "file_name": sub.file_name,
            "file_path": sub.file_path,
            "file_url": sub.file_url,
            "file_type": sub.file_type,
            "extracted_text": sub.extracted_text,
            "content": sub.content or sub.extracted_text or "",
            "file_content": sub.file_content,
            "similarity_score": 0.0,
            "ai_content_probability": 0.0,
            "web_plagiarism_score": 0.0,
            "web_sources": [],
            "status": "pending",
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase single submission sync notice: {e}")

    log_audit_event(
        actor=instructor.name,
        action="CREATE_SUBMISSION",
        entity="Submission",
        entity_id=sub.id,
        details=f"Submission entered for {sub.student_name} ({sub.student_roll})",
    )

    return SubmissionResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student=sub.student_name,
        roll=sub.student_roll,
        file_name=sub.file_name,
        status=sub.status,
        score=0.0,
        similarity=0.0,
        ai_content=0.0,
        web_plagiarism=0.0,
        file_url=sub.file_url,
        created_at=sub.created_at,
    )


@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionResponse])
def get_assignment_submissions(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all submissions for an assignment with decrypted student names,

    file URLs, and plagiarism scores.
    """
    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    if not submissions:
        # Check Supabase database
        try:
            from app.core.supabase import supabase
            res = supabase.table("submissions").select("*").eq("assignment_id", assignment_id).execute()
            if res.data:
                for row in res.data:
                    existing = db.query(Submission).filter(Submission.id == row["id"]).first()
                    if not existing:
                        s = Submission(
                            id=row["id"],
                            assignment_id=row["assignment_id"],
                            student_name_encrypted=row["student_name_encrypted"],
                            student_roll_encrypted=row["student_roll_encrypted"],
                            student_email_encrypted=row.get("student_email_encrypted"),
                            file_name=row["file_name"],
                            file_path=row.get("file_path", ""),
                            file_url=row.get("file_url"),
                            file_type=row.get("file_type", "pdf"),
                            extracted_text=row.get("extracted_text"),
                            content=row.get("content") or row.get("extracted_text") or "",
                            file_content=row.get("file_content"),
                            similarity_score=float(row.get("similarity_score") or 0.0),
                            ai_content_probability=float(row.get("ai_content_probability") or 0.0),
                            web_plagiarism_score=float(row.get("web_plagiarism_score") or 0.0),
                            status=row.get("status", "pending"),
                        )
                        db.add(s)
                db.commit()
                submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
        except Exception as e:
            logger.warning(f"Supabase submissions fetch fallback notice: {e}")

    return [
        SubmissionResponse(
            id=s.id,
            assignment_id=s.assignment_id,
            student=s.student_name,
            roll=s.student_roll,
            file_name=s.file_name,
            status=s.status,
            score=s.draft_grade.final_score if (s.draft_grade and s.draft_grade.final_score is not None) else (s.draft_grade.suggested_score if s.draft_grade else 0.0),
            similarity=s.similarity_score or 0.0,
            ai_content=s.ai_content_probability or 0.0,
            web_plagiarism=s.web_plagiarism_score or 0.0,
            file_url=s.file_url,
            created_at=s.created_at,
        )
        for s in submissions
    ]


@router.delete("/submissions/{submission_id}", status_code=204)
def delete_single_submission(
    submission_id: str,
    db: Session = Depends(get_db),
):
    """Delete a single student submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    try:
        db.delete(sub)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Error deleting submission {submission_id} from local db: {db_err}")

    try:
        from app.core.supabase import supabase
        supabase.table("submissions").delete().eq("id", submission_id).execute()
    except Exception as e:
        logger.warning(f"Supabase submission delete notice: {e}")

    return None


@router.delete("/assignments/{assignment_id}/submissions", status_code=200)
def clear_assignment_submissions(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Clear all submissions for an assignment to allow clean input."""
    subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    count = len(subs)
    try:
        for s in subs:
            db.delete(s)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Error clearing submissions from local db: {db_err}")

    try:
        from app.core.supabase import supabase
        supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
    except Exception as e:
        logger.warning(f"Supabase clear submissions notice: {e}")

    return {"cleared": count}
