"""Submission and Batch Upload API endpoints."""

import os
import uuid
import zipfile
from io import BytesIO
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger, log_audit_event
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate, SubmissionResponse, BatchUploadResponse
from app.services.pdf_service import pdf_service
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(tags=["Submissions"])


def _ensure_assignment_exists(db: Session, assignment_id: str) -> Optional[Assignment]:
    """Ensure assignment exists in local DB, checking and replicating from Supabase if needed."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if assignment:
        return assignment

    try:
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


@router.post("/assignments/{assignment_id}/submissions/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_submissions(
    assignment_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Batch upload student submissions (PDF, TXT, DOCX, ZIP, Code).

    Extracts text, stores files directly in database with FERPA encryption,
    and synchronizes with persistent database storage.
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

    db.commit()

    # Sync created submissions to Supabase database
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
                "file_type": s.file_type,
                "extracted_text": s.extracted_text,
                "file_content": s.file_content,
                "similarity_score": 0.0,
                "ai_content_probability": 0.0,
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


def _create_single_submission(
    db: Session,
    assignment_id: str,
    filename: str,
    content: bytes,
    upload_dir: str,
) -> Submission:
    """Helper to parse student name/roll from filename and persist with FERPA encryption."""
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception:
        file_path = ""

    # Determine file type and format file content string
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

    extracted_text = pdf_service.extract_text_from_bytes(content, filename)
    if not extracted_text and not is_binary:
        extracted_text = file_content_str

    # Heuristic student parsing from filename (e.g., 'sharma_rahul_graphs.pdf')
    clean_stem = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    parts = clean_stem.split()
    if len(parts) >= 2:
        student_name = f"{parts[1].capitalize()} {parts[0].capitalize()}"
    else:
        student_name = clean_stem.capitalize() or "Anonymous Student"

    import random
    roll = f"2024-{random.randint(10, 99):03d}"

    sub = Submission(
        id=f"sub_{uuid.uuid4().hex[:8]}",
        assignment_id=assignment_id,
        file_name=filename,
        file_path=file_path,
        file_type=ext,
        extracted_text=extracted_text,
        file_content=file_content_str,
        status="pending",
    )
    # Uses FERPA transparent encryption setters
    sub.student_name = student_name
    sub.student_roll = roll
    sub.student_email = f"{parts[0].lower() if parts else 'student'}@university.edu"

    db.add(sub)
    return sub


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionResponse)
def create_single_submission(
    assignment_id: str,
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Create a single student submission with manual text entry."""
    assignment = _ensure_assignment_exists(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    sub_id = f"sub_{uuid.uuid4().hex[:8]}"
    sub = Submission(
        id=sub_id,
        assignment_id=assignment_id,
        file_name=f"{payload.student_name.lower().replace(' ', '_')}_submission.txt",
        file_path="",
        file_type="text",
        extracted_text=payload.extracted_text or "",
        file_content=payload.extracted_text or "",
        status="pending",
    )
    sub.student_name = payload.student_name
    sub.student_roll = payload.student_roll
    sub.student_email = payload.student_email or f"{payload.student_name.lower().replace(' ', '.')}@university.edu"

    db.add(sub)
    db.commit()
    db.refresh(sub)

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
            "file_path": "",
            "file_type": "text",
            "extracted_text": sub.extracted_text,
            "file_content": sub.file_content,
            "similarity_score": 0.0,
            "ai_content_probability": 0.0,
            "status": "pending",
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase single submission sync notice: {e}")

    log_audit_event(
        actor=instructor.name,
        action="CREATE_SUBMISSION",
        entity="Submission",
        entity_id=sub.id,
        details=f"Manual submission entered for {payload.student_name} ({payload.student_roll})",
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
        created_at=sub.created_at,
    )


@router.get("/assignments/{assignment_id}/submissions", response_model=List[SubmissionResponse])
def get_assignment_submissions(
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all submissions for an assignment with decrypted student names and plagiarism scores."""
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
                            file_type=row.get("file_type", "pdf"),
                            extracted_text=row.get("extracted_text"),
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

    db.delete(sub)
    db.commit()

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
    for s in subs:
        db.delete(s)
    db.commit()

    try:
        from app.core.supabase import supabase
        supabase.table("submissions").delete().eq("assignment_id", assignment_id).execute()
    except Exception as e:
        logger.warning(f"Supabase clear submissions notice: {e}")

    return {"cleared": count}

