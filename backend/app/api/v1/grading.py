"""AI Grading and Teacher Review Queue API endpoints."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import log_audit_event
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.schemas.grading import (
    GradeApprovalRequest,
    FlagActionRequest,
    DraftGradeResponse,
)
from app.schemas.submission import SubmissionResponse, SubmissionDetailResponse
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(tags=["AI Grading & Teacher Review"])


@router.get("/assignments/{assignment_id}/reviews", response_model=List[SubmissionResponse])
def get_review_queue(
    assignment_id: str,
    status_filter: Optional[str] = None,  # pending, flagged, approved
    db: Session = Depends(get_db),
):
    """Retrieve review queue items for teacher review.

    Every item requires teacher stamp before finalization.
    """
    query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
    if status_filter:
        query = query.filter(Submission.status == status_filter)
    submissions = query.all()

    results = []
    for s in submissions:
        score = 0.0
        if s.draft_grade:
            score = s.draft_grade.final_score if s.draft_grade.final_score is not None else s.draft_grade.suggested_score

        results.append(
            SubmissionResponse(
                id=s.id,
                assignment_id=s.assignment_id,
                student=s.student_name,
                roll=s.student_roll,
                file_name=s.file_name,
                status=s.status,
                score=score,
                similarity=s.similarity_score or 0.0,
                ai_content=s.ai_content_probability or 0.0,
                web_plagiarism=s.web_plagiarism_score or 0.0,
                created_at=s.created_at,
            )
        )
    return results


@router.get("/submissions/{submission_id}/review-detail", response_model=SubmissionDetailResponse)
def get_submission_review_detail(
    submission_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve complete review workspace details including rubric scores,
    matching phrases, AI rationale, and 3-way plagiarism metrics.
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        # Check Supabase
        try:
            from app.core.supabase import supabase
            res = supabase.table("submissions").select("*").eq("id", submission_id).execute()
            if res.data:
                row = res.data[0]
                sub = Submission(
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
                    web_sources=row.get("web_sources") or [],
                    status=row.get("status", "pending"),
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)
        except Exception as e:
            logger.warning(f"Supabase lookup fallback notice: {e}")

    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    draft = sub.draft_grade
    matching_match = (
        db.query(SimilarityMatch)
        .filter((SimilarityMatch.submission_a_id == sub.id) | (SimilarityMatch.submission_b_id == sub.id))
        .first()
    )

    matching_phrase = None
    plagiarised_words = []
    if matching_match and matching_match.matching_phrases:
        matching_phrase = matching_match.matching_phrases[0]
        plagiarised_words = matching_match.matching_phrases

    criteria_scores = draft.criteria_scores if draft else []
    ai_feedback = draft.ai_feedback if draft else ""
    teacher_feedback = draft.teacher_feedback if draft else ""
    current_score = draft.final_score if (draft and draft.final_score is not None) else (draft.suggested_score if draft else 0.0)

    return SubmissionDetailResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student=sub.student_name,
        roll=sub.student_roll,
        file_name=sub.file_name,
        status=sub.status,
        score=current_score,
        similarity=sub.similarity_score or 0.0,
        ai_content=sub.ai_content_probability or 0.0,
        web_plagiarism=sub.web_plagiarism_score or 0.0,
        file_url=sub.file_url,
        created_at=sub.created_at,
        extracted_text=sub.extracted_text,
        content=sub.content or sub.extracted_text,
        matching_phrase=matching_phrase,
        criteria_scores=criteria_scores,
        ai_feedback=ai_feedback,
        teacher_feedback=teacher_feedback,
        web_sources=sub.web_sources or [],
        plagiarised_words=plagiarised_words,
    )


@router.post("/submissions/{submission_id}/evaluate", response_model=SubmissionDetailResponse)
def evaluate_single_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Trigger on-demand 3-way plagiarism and autograding evaluation for a single submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        try:
            from app.core.supabase import supabase
            res = supabase.table("submissions").select("*").eq("id", submission_id).execute()
            if res.data:
                row = res.data[0]
                sub = Submission(
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
                    web_sources=row.get("web_sources") or [],
                    status=row.get("status", "pending"),
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)
        except Exception as e:
            logger.warning(f"Supabase submission lookup notice: {e}")

    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    from app.services.gemini_service import gemini_service
    from app.services.supabase_service import supabase_service
    from app.services.ferpa_service import ferpa_service
    from app.models.assignment import Assignment
    from app.workers.evaluation_tasks import _ensure_assignment_in_db

    assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    if not assignment:
        assignment = _ensure_assignment_in_db(db, sub.assignment_id)
    rubric_criteria = [
        {"name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0},
        {"name": "Accuracy", "description": "Correctness of algorithmic solution", "weight": 40.0, "max_score": 40.0},
        {"name": "Presentation", "description": "Structure and clarity", "weight": 30.0, "max_score": 30.0},
    ]

    # Fetch peer submissions for peer-to-peer corpus
    peer_subs = supabase_service.get_peer_submissions(sub.assignment_id, exclude_submission_id=sub.id)
    peer_corpus = "\n---\n".join([
        f"Peer Submission {p['id']} ({p.get('student_name', 'Student')}):\n{p.get('extracted_text', '')[:2000]}"
        for p in peer_subs[:8]
    ]) if peer_subs else "No other peer submissions available."

    pseudo_id, sanitized_text = ferpa_service.prepare_for_ai_evaluation(
        submission_id=sub.id,
        student_name=sub.student_name,
        student_roll=sub.student_roll,
        student_email=sub.student_email,
        text_content=sub.extracted_text or sub.content or "",
    )

    ai_result = gemini_service.evaluate_submission(
        submission_text=sanitized_text,
        rubric_criteria=rubric_criteria,
        assignment_title=assignment.title if assignment else "Assignment",
        reference_assignment_text=assignment.reference_assignment_text if assignment else None,
        peer_submissions_context=peer_corpus,
    )

    sub.ai_content_probability = ai_result.ai_generated_probability or 0.0
    if ai_result.web_plagiarism_pct is not None:
        sub.web_plagiarism_score = ai_result.web_plagiarism_pct
    if ai_result.web_sources:
        sub.web_sources = ai_result.web_sources
    if ai_result.peer_to_peer_plagiarism_pct and ai_result.peer_to_peer_plagiarism_pct > (sub.similarity_score or 0.0):
        sub.similarity_score = ai_result.peer_to_peer_plagiarism_pct

    is_flagged = (
        (sub.similarity_score >= 90.0)
        or (sub.ai_content_probability >= 65.0)
        or (sub.web_plagiarism_score >= 25.0)
    )
    sub.status = "flagged" if is_flagged else "graded"

    criteria_payload = [
        {
            "criterion_name": c.criterion_name,
            "score": c.awarded_score,
            "max": c.max_score,
            "rationale": c.rationale,
        }
        for c in ai_result.criteria_evaluations
    ]

    draft = sub.draft_grade
    if not draft:
        draft = DraftGrade(
            id=f"draft_{uuid.uuid4().hex[:12]}",
            submission_id=sub.id,
            suggested_score=ai_result.overall_score,
            criteria_scores=criteria_payload,
            ai_feedback=ai_result.feedback_summary,
            status="flagged" if is_flagged else "pending",
            ai_model=settings.GEMINI_MODEL,
        )
        db.add(draft)
    else:
        draft.suggested_score = ai_result.overall_score
        draft.criteria_scores = criteria_payload
        draft.ai_feedback = ai_result.feedback_summary
        draft.status = "flagged" if is_flagged else "pending"

    db.commit()

    # Sync to Supabase
    try:
        supabase_service.save_evaluation_results(
            submission_id=sub.id,
            overall_score=ai_result.overall_score,
            similarity_score=sub.similarity_score,
            ai_content_probability=sub.ai_content_probability,
            web_plagiarism_score=sub.web_plagiarism_score,
            web_sources=sub.web_sources or [],
            criteria_scores=criteria_payload,
            ai_feedback=ai_result.feedback_summary,
            is_flagged=is_flagged,
        )
    except Exception as e:
        logger.warning(f"Supabase evaluation save error: {e}")

    return get_submission_review_detail(submission_id=sub.id, db=db)


@router.put("/submissions/{submission_id}/stamp-grade", response_model=DraftGradeResponse)
def stamp_grade(
    submission_id: str,
    payload: GradeApprovalRequest,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Teacher stamps final approval or saves edits on a draft grade.

    AI NEVER finalizes a grade alone; teacher is always the final authority.
    """
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    draft = sub.draft_grade
    if not draft:
        draft = DraftGrade(
            id=f"draft_{submission_id}",
            submission_id=submission_id,
            suggested_score=payload.final_score,
            criteria_scores=[],
            status="approved",
        )
        db.add(draft)

    draft.final_score = payload.final_score
    if payload.teacher_feedback is not None:
        draft.teacher_feedback = payload.teacher_feedback

    if payload.criteria_scores:
        draft.criteria_scores = [c.dict() for c in payload.criteria_scores]

    if payload.action == "APPROVE":
        draft.status = "approved"
        draft.approved_at = datetime.utcnow()
        draft.approved_by_id = instructor.id
        sub.status = "approved"
    else:
        draft.status = "pending"

    db.commit()
    db.refresh(draft)

    log_audit_event(
        actor=instructor.name,
        action=f"GRADE_{payload.action}",
        entity="Submission",
        entity_id=submission_id,
        details=f"Final score: {draft.final_score}, Teacher Feedback: '{draft.teacher_feedback}'",
    )

    return DraftGradeResponse(
        id=draft.id,
        submission_id=draft.submission_id,
        suggested_score=draft.suggested_score,
        final_score=draft.final_score,
        criteria_scores=draft.criteria_scores,
        ai_feedback=draft.ai_feedback,
        teacher_feedback=draft.teacher_feedback,
        status=draft.status,
        ai_model=draft.ai_model,
        approved_at=draft.approved_at,
    )


@router.post("/submissions/{submission_id}/flag-action")
def take_flag_action(
    submission_id: str,
    payload: FlagActionRequest,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Teacher action on similarity/AI flags: CONFIRM_CONCERN, DISMISS_FLAG, ADD_NOTE."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    matches = (
        db.query(SimilarityMatch)
        .filter((SimilarityMatch.submission_a_id == sub.id) | (SimilarityMatch.submission_b_id == sub.id))
        .all()
    )

    for m in matches:
        if payload.action == "CONFIRM_CONCERN":
            m.status = "Confirmed concern"
        elif payload.action == "DISMISS_FLAG":
            m.status = "Dismissed"
        if payload.note:
            m.teacher_note = payload.note

    if payload.action == "DISMISS_FLAG":
        if sub.status == "flagged":
            sub.status = "graded"
    elif payload.action == "CONFIRM_CONCERN":
        sub.status = "flagged"

    db.commit()

    log_audit_event(
        actor=instructor.name,
        action=f"FLAG_{payload.action}",
        entity="Submission",
        entity_id=submission_id,
        details=payload.note or "",
    )

    return {"message": f"Flag action {payload.action} recorded successfully"}
