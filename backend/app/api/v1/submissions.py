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


@router.post("/assignments/{assignment_id}/submissions/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_submissions(
    assignment_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Batch upload student submissions (PDF, TXT, DOCX, ZIP).

    Extracts text, stores files, and registers submissions with FERPA
    encryption.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
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

    extracted_text = pdf_service.extract_text_from_bytes(content, filename)

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
        extracted_text=extracted_text,
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
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
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
        status="pending",
    )
    sub.student_name = payload.student_name
    sub.student_roll = payload.student_roll
    sub.student_email = payload.student_email or f"{payload.student_name.lower().replace(' ', '.')}@university.edu"

    db.add(sub)
    db.commit()
    db.refresh(sub)

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

