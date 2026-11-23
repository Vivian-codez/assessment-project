# Module docstring explaining AI Grading and Teacher Review Queue API endpoints
"""AI Grading and Teacher Review Queue API endpoints."""

# Import uuid library for generating unique IDs for drafts
import uuid
# Import datetime class for UTC timestamp recording
from datetime import datetime
# Import typing annotations for lists and optional variables
from typing import List, Optional
# Import FastAPI routing constructs, dependency injection, and HTTP exceptions
from fastapi import APIRouter, Depends, HTTPException
# Import SQLAlchemy Session type for database operations
from sqlalchemy.orm import Session

# Import get_db dependency helper to obtain a database session
from app.core.database import get_db
# Import logger and log_audit_event from logging core
from app.core.logging import logger, log_audit_event
# Import application configuration settings
from app.core.config import settings
# Import Submission database model
from app.models.submission import Submission
# Import DraftGrade database model
from app.models.draft_grade import DraftGrade
# Import SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch
# Import grading request and response schemas
from app.schemas.grading import (
    GradeApprovalRequest,
    FlagActionRequest,
    DraftGradeResponse,
)
# Import submission summary and detail response schemas
from app.schemas.submission import SubmissionResponse, SubmissionDetailResponse
# Import dependency to resolve the authenticated instructor
from app.api.v1.auth import get_current_instructor
# Import Instructor database model
from app.models.instructor import Instructor

# Initialize API router with OpenAPI tag for grading and teacher review
router = APIRouter(tags=["AI Grading & Teacher Review"])


# Route handler to retrieve review queue items for an assignment
@router.get("/assignments/{assignment_id}/reviews", response_model=List[SubmissionResponse])
# Define endpoint function accepting assignment ID, optional status filter, and db session
def get_review_queue(
    # Assignment ID path parameter
    assignment_id: str,
    # Optional query filter for submission status
    status_filter: Optional[str] = None,  # pending, flagged, approved
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining teacher review queue retrieval
    """Retrieve review queue items for teacher review.

    Every item requires teacher stamp before finalization.
    """
    # Build query filtering submissions by assignment ID
    query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
    # Check if a status filter was specified
    if status_filter:
        # Filter query by matching submission status
        query = query.filter(Submission.status == status_filter)
    # Execute query to fetch all matching submissions
    submissions = query.all()

    # Initialize results list for formatted submission responses
    results = []
    # Iterate through retrieved submissions
    for s in submissions:
        # Default submission score to 0.0
        score = 0.0
        # Check if submission has an associated draft grade
        if s.draft_grade:
            # Use final score if teacher stamped, otherwise suggested score
            score = s.draft_grade.final_score if s.draft_grade.final_score is not None else s.draft_grade.suggested_score

        # Append formatted SubmissionResponse schema to results list
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
    # Return list of formatted submission review items
    return results


# Route handler to retrieve full review workspace details for a single submission
@router.get("/submissions/{submission_id}/review-detail", response_model=SubmissionDetailResponse)
# Define endpoint function accepting submission ID and db session
def get_submission_review_detail(
    # Submission ID path parameter
    submission_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Docstring explaining retrieval of full review workspace details
    """Retrieve complete review workspace details including rubric scores,
    matching phrases, AI rationale, and 3-way plagiarism metrics.
    """
    # Query local database for submission by ID
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # If submission is not found locally, attempt sync from Supabase
    if not sub:
        # Check Supabase
        # Begin try block for remote lookup
        try:
            # Import Supabase client
            from app.core.supabase import supabase
            # Query Supabase submissions table by ID
            res = supabase.table("submissions").select("*").eq("id", submission_id).execute()
            # If submission row found remotely, instantiate local model
            if res.data:
                # Extract first matching row dictionary
                row = res.data[0]
                # Instantiate Submission model with remote row attributes
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
                # Add submission to database session
                db.add(sub)
                # Commit mirrored submission to database
                db.commit()
                # Refresh submission model instance
                db.refresh(sub)
        # Catch any remote lookup exceptions
        except Exception as e:
            # Log warning notice for failed remote submission lookup
            logger.warning(f"Supabase lookup fallback notice: {e}")

    # If submission still not found, return 404
    if not sub:
        # Raise HTTP 404 exception indicating submission not found
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get associated draft grade model
    draft = sub.draft_grade
    # Query for any similarity match involving this submission
    matching_match = (
        db.query(SimilarityMatch)
        .filter((SimilarityMatch.submission_a_id == sub.id) | (SimilarityMatch.submission_b_id == sub.id))
        .first()
    )

    # Initialize matching phrase variable as None
    matching_phrase = None
    # Initialize list of plagiarised phrases
    plagiarised_words = []
    # If matching match record has phrases, extract primary phrase and list
    if matching_match and matching_match.matching_phrases:
        # Set primary matching phrase
        matching_phrase = matching_match.matching_phrases[0]
        # Set list of plagiarized phrases
        plagiarised_words = matching_match.matching_phrases

    # Extract criteria scores list from draft or default to empty list
    criteria_scores = draft.criteria_scores if draft else []
    # Extract AI feedback text from draft or default to empty string
    ai_feedback = draft.ai_feedback if draft else ""
    # Extract teacher feedback text from draft or default to empty string
    teacher_feedback = draft.teacher_feedback if draft else ""
    # Determine current score from final score or suggested score
    current_score = draft.final_score if (draft and draft.final_score is not None) else (draft.suggested_score if draft else 0.0)

    # Format and return complete SubmissionDetailResponse schema
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


# Route handler to trigger on-demand evaluation of a single submission
@router.post("/submissions/{submission_id}/evaluate", response_model=SubmissionDetailResponse)
# Define endpoint function accepting submission ID, db session, and authenticated instructor
def evaluate_single_submission(
    # Submission ID path parameter
    submission_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining on-demand single submission evaluation
    """Trigger on-demand 3-way plagiarism and autograding evaluation for a single submission."""
    # Query local database for submission by ID
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # If submission is not found locally, attempt sync from Supabase
    if not sub:
        # Begin try block for remote lookup
        try:
            # Import Supabase client
            from app.core.supabase import supabase
            # Query Supabase submissions table by ID
            res = supabase.table("submissions").select("*").eq("id", submission_id).execute()
            # If submission row found remotely, instantiate local model
            if res.data:
                # Extract first matching row dictionary
                row = res.data[0]
                # Instantiate Submission model
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
                # Add submission to database session
                db.add(sub)
                # Commit mirrored submission to database
                db.commit()
                # Refresh submission model instance
                db.refresh(sub)
        # Catch any remote lookup exceptions
        except Exception as e:
            # Log warning notice for failed remote submission lookup
            logger.warning(f"Supabase submission lookup notice: {e}")

    # Check if submission is still not found
    if not sub:
        # Raise HTTP 404 exception indicating submission not found
        raise HTTPException(status_code=404, detail="Submission not found")

    # Import gemini_service for AI evaluation
    from app.services.gemini_service import gemini_service
    # Import supabase_service for cloud data syncing
    from app.services.supabase_service import supabase_service
    # Import ferpa_service for PII sanitization
    from app.services.ferpa_service import ferpa_service
    # Import Assignment database model
    from app.models.assignment import Assignment
    # Import helper function to ensure assignment exists
    from app.workers.evaluation_tasks import _ensure_assignment_in_db

    # Query local database for assignment
    assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    # If assignment not found locally, ensure it exists in database
    if not assignment:
        # Ensure assignment exists in database and fetch instance
        assignment = _ensure_assignment_in_db(db, sub.assignment_id)
    # Define standard rubric criteria list for evaluation
    rubric_criteria = [
        {"name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0},
        {"name": "Accuracy", "description": "Correctness of algorithmic solution", "weight": 40.0, "max_score": 40.0},
        {"name": "Presentation", "description": "Structure and clarity", "weight": 30.0, "max_score": 30.0},
    ]

    # Fetch peer submissions for peer-to-peer corpus
    # Retrieve peer submissions excluding the current submission
    peer_subs = supabase_service.get_peer_submissions(sub.assignment_id, exclude_submission_id=sub.id)
    # Join peer submission text snippets into peer corpus string
    peer_corpus = "\n---\n".join([
        f"Peer Submission {p['id']} ({p.get('student_name', 'Student')}):\n{p.get('extracted_text', '')[:2000]}"
        for p in peer_subs[:8]
    ]) if peer_subs else "No other peer submissions available."

    # Prepare sanitized text stripping PII under FERPA guidelines
    pseudo_id, sanitized_text = ferpa_service.prepare_for_ai_evaluation(
        submission_id=sub.id,
        student_name=sub.student_name,
        student_roll=sub.student_roll,
        student_email=sub.student_email,
        text_content=sub.extracted_text or sub.content or "",
    )

    # Call Gemini service to evaluate the submission against rubric and peer context
    ai_result = gemini_service.evaluate_submission(
        submission_text=sanitized_text,
        rubric_criteria=rubric_criteria,
        assignment_title=assignment.title if assignment else "Assignment",
        reference_assignment_text=assignment.reference_assignment_text if assignment else None,
        peer_submissions_context=peer_corpus,
    )

    # Update submission AI generated content probability score
    sub.ai_content_probability = ai_result.ai_generated_probability or 0.0
    # Update submission web plagiarism score if returned
    if ai_result.web_plagiarism_pct is not None:
        # Set web plagiarism score
        sub.web_plagiarism_score = ai_result.web_plagiarism_pct
    # Update matched web sources list
    if ai_result.web_sources:
        # Set web sources
        sub.web_sources = ai_result.web_sources
    # Update peer similarity score if AI detected higher similarity
    if ai_result.peer_to_peer_plagiarism_pct and ai_result.peer_to_peer_plagiarism_pct > (sub.similarity_score or 0.0):
        # Set peer similarity score
        sub.similarity_score = ai_result.peer_to_peer_plagiarism_pct

    # Determine if plagiarism thresholds trigger a review flag
    is_flagged = (
        (sub.similarity_score >= 90.0)
        or (sub.ai_content_probability >= 65.0)
        or (sub.web_plagiarism_score >= 25.0)
    )
    # Set submission status based on flag determination
    sub.status = "flagged" if is_flagged else "graded"

    # Build criteria evaluation payload list for persistence
    criteria_payload = [
        {
            "criterion_name": c.criterion_name,
            "score": c.awarded_score,
            "max": c.max_score,
            "rationale": c.rationale,
        }
        for c in ai_result.criteria_evaluations
    ]

    # Retrieve existing draft grade for this submission
    draft = sub.draft_grade
    # If no draft exists, create a new DraftGrade record
    if not draft:
        # Instantiate new DraftGrade entity
        draft = DraftGrade(
            id=f"draft_{uuid.uuid4().hex[:12]}",
            submission_id=sub.id,
            suggested_score=ai_result.overall_score,
            criteria_scores=criteria_payload,
            ai_feedback=ai_result.feedback_summary,
            status="flagged" if is_flagged else "pending",
            ai_model=settings.GEMINI_MODEL,
        )
        # Add new draft grade to database session
        db.add(draft)
    # If draft already exists, update its attributes
    else:
        # Update suggested score
        draft.suggested_score = ai_result.overall_score
        # Update criteria breakdown scores
        draft.criteria_scores = criteria_payload
        # Update AI feedback summary
        draft.ai_feedback = ai_result.feedback_summary
        # Update draft status
        draft.status = "flagged" if is_flagged else "pending"

    # Commit evaluation updates to local database
    db.commit()

    # Sync to Supabase
    # Begin try block to mirror evaluation results in Supabase
    try:
        # Call supabase_service to save evaluation results remotely
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
    # Catch any exceptions during Supabase evaluation sync
    except Exception as e:
        # Log warning notice for remote evaluation save error
        logger.warning(f"Supabase evaluation save error: {e}")

    # Return refreshed submission review detail response
    return get_submission_review_detail(submission_id=sub.id, db=db)


# Route handler for teacher stamping final grade approval or edits
@router.put("/submissions/{submission_id}/stamp-grade", response_model=DraftGradeResponse)
# Define endpoint function accepting submission ID, approval payload, db session, and instructor
def stamp_grade(
    # Submission ID path parameter
    submission_id: str,
    # Grade approval payload from request body
    payload: GradeApprovalRequest,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining teacher stamp approval requirement
    """Teacher stamps final approval or saves edits on a draft grade.

    AI NEVER finalizes a grade alone; teacher is always the final authority.
    """
    # Query local database for submission by ID
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # If submission does not exist, return 404
    if not sub:
        # Raise HTTP 404 exception indicating submission not found
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get associated draft grade model
    draft = sub.draft_grade
    # If no draft grade exists yet, instantiate one
    if not draft:
        # Create new DraftGrade entity
        draft = DraftGrade(
            id=f"draft_{submission_id}",
            submission_id=submission_id,
            suggested_score=payload.final_score,
            criteria_scores=[],
            status="approved",
        )
        # Add draft grade to database session
        db.add(draft)

    # Set final score stamped by teacher
    draft.final_score = payload.final_score
    # Check if teacher feedback is provided
    if payload.teacher_feedback is not None:
        # Update teacher qualitative feedback
        draft.teacher_feedback = payload.teacher_feedback

    # Check if specific criteria scores were adjusted
    if payload.criteria_scores:
        # Store adjusted criteria scores list as dictionaries
        draft.criteria_scores = [c.dict() for c in payload.criteria_scores]

    # Check if teacher action is APPROVE
    if payload.action == "APPROVE":
        # Mark draft status as approved
        draft.status = "approved"
        # Record approval timestamp in UTC
        draft.approved_at = datetime.utcnow()
        # Record ID of approving instructor
        draft.approved_by_id = instructor.id
        # Update submission status to approved
        sub.status = "approved"
    # Otherwise set status to pending
    else:
        # Set draft status to pending
        draft.status = "pending"

    # Commit grade changes to database
    db.commit()
    # Refresh draft instance
    db.refresh(draft)

    # Log grade stamping audit event
    log_audit_event(
        actor=instructor.name,
        action=f"GRADE_{payload.action}",
        entity="Submission",
        entity_id=submission_id,
        details=f"Final score: {draft.final_score}, Teacher Feedback: '{draft.teacher_feedback}'",
    )

    # Return formatted DraftGradeResponse schema
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


# Route handler for taking teacher action on plagiarism/AI flags
@router.post("/submissions/{submission_id}/flag-action")
# Define endpoint function accepting submission ID, flag action payload, db session, and instructor
def take_flag_action(
    # Submission ID path parameter
    submission_id: str,
    # Flag action payload from request body
    payload: FlagActionRequest,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Injected authenticated instructor dependency
    instructor: Instructor = Depends(get_current_instructor),
):
    # Docstring explaining teacher flag actions
    """Teacher action on similarity/AI flags: CONFIRM_CONCERN, DISMISS_FLAG, ADD_NOTE."""
    # Query local database for submission by ID
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # Check if submission does not exist
    if not sub:
        # Raise HTTP 404 exception indicating submission not found
        raise HTTPException(status_code=404, detail="Submission not found")

    # Query all similarity matches involving this submission
    matches = (
        db.query(SimilarityMatch)
        .filter((SimilarityMatch.submission_a_id == sub.id) | (SimilarityMatch.submission_b_id == sub.id))
        .all()
    )

    # Iterate through all related similarity matches
    for m in matches:
        # Check if action is confirming concern
        if payload.action == "CONFIRM_CONCERN":
            # Set match status to Confirmed concern
            m.status = "Confirmed concern"
        # Check if action is dismissing flag
        elif payload.action == "DISMISS_FLAG":
            # Set match status to Dismissed
            m.status = "Dismissed"
        # Check if teacher note was provided
        if payload.note:
            # Set teacher note on match record
            m.teacher_note = payload.note

    # Check if teacher dismissed the flag
    if payload.action == "DISMISS_FLAG":
        # If submission was flagged, change status back to graded
        if sub.status == "flagged":
            # Update submission status to graded
            sub.status = "graded"
    # Check if teacher confirmed the concern
    elif payload.action == "CONFIRM_CONCERN":
        # Set submission status to flagged
        sub.status = "flagged"

    # Commit flag action changes to database
    db.commit()

    # Log flag action audit event
    log_audit_event(
        actor=instructor.name,
        action=f"FLAG_{payload.action}",
        entity="Submission",
        entity_id=submission_id,
        details=payload.note or "",
    )

    # Return success confirmation message
    return {"message": f"Flag action {payload.action} recorded successfully"}
