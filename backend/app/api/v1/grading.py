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
        created_at=sub.created_at,
        extracted_text=sub.extracted_text,
        matching_phrase=matching_phrase,
        criteria_scores=criteria_scores,
        ai_feedback=ai_feedback,
        teacher_feedback=teacher_feedback,
        web_sources=sub.web_sources or [],
        plagiarised_words=plagiarised_words,
    )


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
