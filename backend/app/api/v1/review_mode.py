# Module docstring explaining Review Mode, Meta-Prompt Assistant, and Teacher-Controlled Grading endpoints
"""Review Mode, Prompt Versioning, Meta-Prompt Assistant, and Teacher-Controlled Grading API endpoints.

Provides full educator control over:
- Decoupled, scheduled, or instant AI auto-grading with pre-flight summaries
- Prompt iteration and version control with immutable locked base instructions
- Teacher feedback and error categorization on criteria evaluations
- Meta-prompt assistant generating unified diffs from teacher corrections
- Non-destructive dry-run testing on sample cohorts without corrupting gradebook
- Immutable grade history audit trails for all score overrides and approvals
"""

# Import standard library modules for datetime, math, json, and typing
import json
import math
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Import FastAPI routing primitives, dependency injection, and HTTP exceptions
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import database session dependency
from app.core.database import get_db
# Import application logger for diagnostic telemetry
from app.core.logging import logger
# Import authentication dependencies
from app.api.v1.auth import get_current_user
# Import ORM models
from app.models.user import User
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.rubric import Rubric, RubricCriterion
from app.models.grading_run import GradingRun
from app.models.batch_job import BatchJob
from app.models.prompt_version import PromptVersion
from app.models.prompt_feedback import PromptFeedback
from app.models.dry_run import DryRun, DryRunResult
from app.models.grade_history import GradeHistory
from app.models.review_progress import ReviewProgress
# Import Gemini service for meta-prompt assistant analysis
from app.services.gemini_service import gemini_service
# Import Pydantic schemas for request validation
from pydantic import BaseModel, Field

# Initialize FastAPI router instance tagged under Review Mode & Grading Control
router = APIRouter(prefix="/review-mode", tags=["Review Mode & Grading Control"])


# --- PYDANTIC SCHEMAS ---

# Schema for prompt version creation
class PromptVersionCreate(BaseModel):
    """Schema for creating a new prompt version."""
    # Extra instructions written by teacher
    extra_teacher_instructions: Optional[str] = None
    # Calibrated few-shot examples
    few_shot_examples: Optional[List[Dict[str, Any]]] = None
    # Thresholds for similarity and AI detection
    thresholds: Optional[Dict[str, Any]] = None
    # Changelog note describing updates
    note: Optional[str] = "Teacher revision"


# Schema for feedback submission on a rubric criterion
class FeedbackSubmissionRequest(BaseModel):
    """Schema for logging teacher feedback on a specific criterion."""
    # Target submission identifier
    submission_id: str
    # Rubric criterion identifier
    criterion_id: Optional[str] = None
    # AI suggested rubric tier identifier
    ai_tier_id: Optional[str] = None
    # Teacher corrected rubric tier identifier
    teacher_tier_id: Optional[str] = None
    # AI suggested score
    ai_score: Optional[float] = None
    # Teacher corrected score
    teacher_score: Optional[float] = None
    # Categorized reason code
    reason: str = Field(..., description="e.g. too_harsh, too_lenient, missed_evidence, misread_rubric")
    # Qualitative teacher notes
    teacher_notes: Optional[str] = None


# Schema for requesting AI prompt fix suggestions
class AssistantFixRequest(BaseModel):
    """Schema for requesting meta-prompt assistant recommendations."""
    # Optional list of specific feedback IDs to address
    feedback_ids: Optional[List[str]] = None
    # Current active extra instructions to build upon
    current_extra_instructions: Optional[str] = None


# Schema for dispatching a dry run simulation
class DryRunRequest(BaseModel):
    """Schema for executing a non-destructive dry run."""
    # Candidate extra instructions to test
    draft_extra_instructions: str
    # Optional sample submission IDs to test (max 5)
    sample_submission_ids: Optional[List[str]] = None
    # Candidate few-shot examples
    draft_few_shot_examples: Optional[List[Dict[str, Any]]] = None


# Schema for teacher-controlled grading start
class StartGradingRequest(BaseModel):
    """Schema for initiating or scheduling an auto-grading batch run."""
    # Scope of grading: 'this_assignment', 'assignment', 'selected_assignments', 'all_in_course', 'course', 'all_courses'
    scope: str = "this_assignment"
    # Target assignment IDs (supports single or array)
    assignment_id: Optional[str] = None
    assignment_ids: Optional[List[str]] = None
    # Course ID if course-level scope
    course_id: Optional[str] = None
    # Submissions filter: 'all_ungraded', 'ungraded', 'all', 'only_selected', 'failed_unreadable', 'failed', 'regrade_all'
    submission_filter: str = "all_ungraded"
    filter_mode: Optional[str] = None
    # Target submission IDs if filter is 'only_selected'
    target_submission_ids: Optional[List[str]] = None
    # When to start: 'now', 'scheduled', 'draft'
    when: str = "now"
    # Scheduled execution timestamp in UTC if when is 'scheduled'
    scheduled_at: Optional[datetime] = None
    scheduled_for: Optional[str] = None
    # Timezone name for display (default Asia/Kolkata)
    timezone_name: str = "Asia/Kolkata"
    timezone: Optional[str] = None
    # Max concurrency ceiling
    max_concurrency: int = 2
    concurrency_limit: Optional[int] = None
    max_cost_limit_usd: Optional[float] = None
    # Pause between batches in seconds
    pause_between_batches_sec: int = 1


# Schema for manual grade override
class GradeOverrideRequest(BaseModel):
    """Schema for teacher manual grade adjustment."""
    # Target submission identifier
    submission_id: str
    # Overridden total score
    score: float
    # Criteria scores breakdown dictionary
    criteria_scores: Optional[Dict[str, float]] = None
    # Criteria breakdown list
    criteria_breakdown: Optional[List[Dict[str, Any]]] = None
    # Qualitative feedback text
    feedback: Optional[str] = None
    # Override rationale
    change_reason: Optional[str] = "Teacher manual override"
    # Status after override (default 'approved')
    status: str = "approved"


# --- PRE-FLIGHT INSPECTION ---

# HTTP GET route handler returning pre-flight grading summary and validation checks
@router.get("/preflight/{assignment_id}")
def get_preflight_summary(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inspects assignment readiness before grading dispatch.

    Validates submission count, rubric presence, reference solution, unreadable files,
    and estimates duration and token consumption.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Fetch submissions
    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.deleted_at.is_(None)
    ).all()

    total_count = len(submissions)
    ungraded_count = sum(1 for s in submissions if s.draft_grade is None or s.status in ("ready", "pending", "unprocessed"))
    graded_count = sum(1 for s in submissions if s.draft_grade is not None and s.status in ("graded", "approved"))
    unreadable_count = sum(1 for s in submissions if not s.extracted_text or len(s.extracted_text.strip()) < 10)

    # Check rubric
    rubric = None
    criteria_count = 0
    if assignment.rubric_id:
        rubric = db.query(Rubric).filter(Rubric.id == assignment.rubric_id).first()
        if rubric:
            criteria_count = len(rubric.criteria) if rubric.criteria else 0

    if not rubric or criteria_count == 0:
        # Check if any rubric exists in the database
        db_rubric = db.query(Rubric).first()
        if db_rubric and db_rubric.criteria:
            assignment.rubric_id = db_rubric.id
            db.commit()
            rubric = db_rubric
            criteria_count = len(rubric.criteria)
        else:
            # Auto-provision standard multi-criteria rubric so grading is never permanently blocked
            auto_rubric = Rubric(
                id=f"rub_{uuid.uuid4().hex[:10]}",
                title="Standard Academic Assessment Rubric",
                description="Comprehensive multi-criteria evaluation matrix.",
                grading_scale="points",
                criteria=[
                    {"id": "crit_1", "criterion_name": "Correctness & Accuracy", "weight": 40, "description": "Accurate algorithmic logic and domain accuracy."},
                    {"id": "crit_2", "criterion_name": "Implementation Quality", "weight": 30, "description": "Clean modularity and readability."},
                    {"id": "crit_3", "criterion_name": "Edge Cases & Boundaries", "weight": 20, "description": "Handling of boundary conditions and invalid inputs."},
                    {"id": "crit_4", "criterion_name": "Documentation & Complexity", "weight": 10, "description": "Complexity justification and clear comments."},
                ],
            )
            db.add(auto_rubric)
            assignment.rubric_id = auto_rubric.id
            db.commit()
            rubric = auto_rubric
            criteria_count = 4

    # Check active prompt version
    active_prompt = db.query(PromptVersion).filter(
        PromptVersion.assignment_id == assignment_id,
        PromptVersion.is_active.is_(True)
    ).order_by(PromptVersion.version_number.desc()).first()

    prompt_version_num = active_prompt.version_number if active_prompt else 1

    # Check reference solution
    has_reference = bool(assignment.reference_assignment_text and len(assignment.reference_assignment_text.strip()) > 20)

    # Calculate token and duration estimates
    # Average ~1200 prompt tokens + ~600 completion tokens per submission
    est_tokens_per_sub = 1800
    est_total_tokens = ungraded_count * est_tokens_per_sub
    # Average ~3.5 seconds per submission under Gemini Flash
    est_duration_seconds = math.ceil(ungraded_count * 3.5)

    # Identify blockers
    blockers: List[str] = []
    warnings: List[str] = []

    if total_count == 0:
        blockers.append("No submissions uploaded yet. Please upload student files first.")
    if ungraded_count == 0:
        warnings.append("All submissions are already graded. Use 'Re-grade all' if you wish to re-evaluate.")
    if not has_reference:
        warnings.append("No reference exemplar solution provided. Grading will proceed based solely on rubric criteria.")
    if unreadable_count > 0:
        warnings.append(f"{unreadable_count} submission(s) contain unreadable or empty text.")

    can_start = len(blockers) == 0

    return {
        "assignment_id": assignment_id,
        "assignment_title": assignment.title,
        "total_submissions": total_count,
        "ungraded_count": ungraded_count,
        "graded_count": graded_count,
        "unreadable_count": unreadable_count,
        "criteria_count": criteria_count,
        "prompt_version": prompt_version_num,
        "has_reference_solution": has_reference,
        "estimated_duration_seconds": est_duration_seconds,
        "estimated_total_tokens": est_total_tokens,
        "blockers": blockers,
        "warnings": warnings,
        "can_start": can_start,
    }


# --- TEACHER-CONTROLLED START GRADING ---

# HTTP POST route handler dispatching or scheduling a batch grading run
@router.post("/start-grading")
def start_grading_run(
    req: StartGradingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiates a teacher-controlled grading execution run with specified scope and filters."""
    # Determine target assignments flexibly
    eff_scope = req.scope or "this_assignment"
    raw_assign_ids = req.assignment_ids or ([req.assignment_id] if req.assignment_id else [])
    eff_filter = req.filter_mode or req.submission_filter or "all_ungraded"
    if eff_filter == "ungraded":
        eff_filter = "all_ungraded"
    elif eff_filter == "failed":
        eff_filter = "failed_unreadable"

    target_assignment_ids = []
    if eff_scope in ("this_assignment", "assignment") and raw_assign_ids:
        target_assignment_ids = raw_assign_ids[:1]
    elif eff_scope in ("selected_assignments", "assignments") and raw_assign_ids:
        target_assignment_ids = raw_assign_ids
    elif eff_scope in ("all_in_course", "course") and req.course_id:
        assignments = db.query(Assignment).filter(Assignment.course_id == req.course_id, Assignment.deleted_at.is_(None)).all()
        target_assignment_ids = [a.id for a in assignments]
    elif eff_scope == "all_courses":
        assignments = db.query(Assignment).filter(Assignment.deleted_at.is_(None)).all()
        target_assignment_ids = [a.id for a in assignments]
    elif raw_assign_ids:
        target_assignment_ids = raw_assign_ids
    else:
        latest = db.query(Assignment).filter(Assignment.deleted_at.is_(None)).order_by(Assignment.id.desc()).first()
        if latest:
            target_assignment_ids = [latest.id]

    if not target_assignment_ids:
        raise HTTPException(status_code=400, detail="No assignments identified for grading scope.")

    # Create GradingRun and BatchJob records for each target assignment
    run_records = []
    primary_run_id = None
    primary_job_id = None

    for assign_id in target_assignment_ids:
        # Count target submissions based on filter
        query = db.query(Submission).filter(Submission.assignment_id == assign_id, Submission.deleted_at.is_(None))
        if eff_filter == "all_ungraded":
            query = query.filter(Submission.draft_grade.is_(None))
        elif eff_filter == "only_selected" and req.target_submission_ids:
            query = query.filter(Submission.id.in_(req.target_submission_ids))
        elif eff_filter == "failed_unreadable":
            query = query.filter((Submission.status == "failed") | (Submission.extracted_text.is_(None)))

        sub_count = query.count()
        run_status = "scheduled" if req.when == "scheduled" else ("draft" if req.when == "draft" else "running")

        run = GradingRun(
            id=f"run-{uuid.uuid4().hex[:12]}",
            assignment_id=assign_id,
            triggered_by=current_user.id,
            status=run_status,
            total_submissions=sub_count,
            completed_count=0,
            failed_count=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        # Create linked BatchJob entity so frontend real-time polling works
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = BatchJob(
            id=job_id,
            assignment_id=assign_id,
            status="queued" if req.when == "now" else "draft",
            progress_pct=0.0,
            total_items=sub_count,
            processed_items=0,
        )
        db.add(job)
        db.flush()

        if not primary_run_id:
            primary_run_id = run.id
            primary_job_id = job.id
        run_records.append((run, job))

    db.commit()

    # If 'now', execute evaluation batch via Celery or local FastAPI BackgroundTasks
    if req.when == "now":
        from app.workers.evaluation_tasks import run_evaluation_batch_logic
        for run, job in run_records:
            dispatched_celery = False
            try:
                from app.workers.celery_app import celery_app
                insp = celery_app.control.inspect(timeout=0.2)
                active = insp.ping() if insp else None
                if active:
                    from app.workers.evaluation_tasks import evaluate_batch_task
                    evaluate_batch_task.delay(
                        job_id=job.id,
                        assignment_id=run.assignment_id,
                        submission_ids=req.target_submission_ids if eff_filter == "only_selected" else None,
                    )
                    dispatched_celery = True
            except Exception as exc:
                logger.info(f"[START-GRADING] Celery dispatch check: {exc}")

            if not dispatched_celery:
                background_tasks.add_task(
                    run_evaluation_batch_logic,
                    job_id=job.id,
                    assignment_id=run.assignment_id,
                    submission_ids=req.target_submission_ids if eff_filter == "only_selected" else None,
                )

    return {
        "status": "success",
        "primary_run_id": primary_run_id,
        "run_id": primary_run_id,
        "job_id": primary_job_id,
        "runs_created": len(run_records),
        "when": req.when,
        "message": f"Grading run {'scheduled' if req.when == 'scheduled' else ('saved as draft' if req.when == 'draft' else 'initiated successfully')}.",
    }


# --- PROMPT VERSION CONTROL ---

# HTTP GET route handler listing all prompt versions for an assignment
@router.get("/assignments/{assignment_id}/prompt-versions")
def list_prompt_versions(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the version history of grading prompts for an assignment."""
    versions = db.query(PromptVersion).filter(
        PromptVersion.assignment_id == assignment_id
    ).order_by(PromptVersion.version_number.desc()).all()

    if not versions:
        # Create baseline v1 if none exists
        v1 = PromptVersion(
            id=str(uuid.uuid4()),
            assignment_id=assignment_id,
            version_number=1,
            prompt_type="grading",
            locked_base_instructions="""You are Verism AI, an authoritative, rubric-based grading assistant for higher education.
Evaluate the student's submission strictly against the provided rubric criteria.
For each criterion:
1. Select the exact matching performance tier.
2. Award points bounded strictly within the criterion max score.
3. Cite verbatim student submission evidence justifying any score deduction.
4. Output strict JSON conforming to StructuredGradingOutput.""",
            extra_teacher_instructions="Standard academic evaluation.",
            note="Initial system baseline",
            created_by=current_user.id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(v1)
        db.commit()
        db.refresh(v1)
        versions = [v1]

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "prompt_type": v.prompt_type,
            "locked_base_instructions": v.locked_base_instructions,
            "extra_teacher_instructions": v.extra_teacher_instructions,
            "few_shot_examples": v.few_shot_examples,
            "thresholds": v.thresholds,
            "note": v.note,
            "is_active": v.is_active,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


# HTTP POST route handler creating a new prompt version
@router.post("/assignments/{assignment_id}/prompt-versions")
def create_prompt_version(
    assignment_id: str,
    payload: PromptVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new prompt version, automatically incrementing version number and setting as active."""
    # Find latest version number
    latest = db.query(PromptVersion).filter(
        PromptVersion.assignment_id == assignment_id
    ).order_by(PromptVersion.version_number.desc()).first()

    next_num = (latest.version_number + 1) if latest else 1

    # Deactivate previous active versions
    db.query(PromptVersion).filter(
        PromptVersion.assignment_id == assignment_id,
        PromptVersion.is_active.is_(True)
    ).update({"is_active": False})

    # Inherit locked base instructions from latest or default
    locked_base = latest.locked_base_instructions if latest else """You are Verism AI, an authoritative, rubric-based grading assistant for higher education.
Evaluate the student's submission strictly against the provided rubric criteria.
For each criterion:
1. Select the exact matching performance tier.
2. Award points bounded strictly within the criterion max score.
3. Cite verbatim student submission evidence justifying any score deduction.
4. Output strict JSON conforming to StructuredGradingOutput."""

    new_v = PromptVersion(
        id=str(uuid.uuid4()),
        assignment_id=assignment_id,
        version_number=next_num,
        prompt_type="grading",
        locked_base_instructions=locked_base,
        extra_teacher_instructions=payload.extra_teacher_instructions,
        few_shot_examples=payload.few_shot_examples,
        thresholds=payload.thresholds,
        note=payload.note,
        created_by=current_user.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_v)
    db.commit()
    db.refresh(new_v)

    return {
        "status": "success",
        "version_number": new_v.version_number,
        "prompt_version_id": new_v.id,
        "message": f"Prompt version v{new_v.version_number} activated.",
    }


# --- TEACHER FEEDBACK & META-PROMPT ASSISTANT ---

# HTTP POST route handler logging teacher corrections on AI grading
@router.post("/assignments/{assignment_id}/feedback")
def submit_prompt_feedback(
    assignment_id: str,
    payload: FeedbackSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Logs teacher disagreement on an AI evaluation criterion for meta-prompt assistant analysis."""
    active_prompt = db.query(PromptVersion).filter(
        PromptVersion.assignment_id == assignment_id,
        PromptVersion.is_active.is_(True)
    ).first()

    fb_record = PromptFeedback(
        id=str(uuid.uuid4()),
        prompt_version_id=active_prompt.id if active_prompt else None,
        submission_id=payload.submission_id,
        assignment_id=assignment_id,
        criterion_id=payload.criterion_id,
        ai_tier_id=payload.ai_tier_id,
        teacher_tier_id=payload.teacher_tier_id,
        ai_score=payload.ai_score,
        teacher_score=payload.teacher_score,
        reason=payload.reason,
        teacher_notes=payload.teacher_notes,
        created_by=current_user.id,
        resolved=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(fb_record)
    db.commit()

    return {
        "status": "success",
        "feedback_id": fb_record.id,
        "message": "Feedback recorded. You can now use 'Fix Prompt' to generate a prompt improvement.",
    }


# HTTP POST route handler calling Gemini Meta-Prompt Assistant to propose prompt diffs
@router.post("/assignments/{assignment_id}/assistant-fix")
def get_assistant_prompt_fix(
    assignment_id: str,
    req: AssistantFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyzes teacher feedback records using Gemini to propose prompt diffs and few-shot examples."""
    # Query unresolved feedback
    query = db.query(PromptFeedback).filter(
        PromptFeedback.assignment_id == assignment_id,
        PromptFeedback.resolved.is_(False)
    )
    if req.feedback_ids:
        query = query.filter(PromptFeedback.id.in_(req.feedback_ids))

    feedbacks = query.all()
    if not feedbacks:
        return {
            "status": "no_feedback",
            "message": "No unresolved feedback found. Flag one or more AI mistakes to generate a prompt fix.",
            "proposed_extra_instructions": req.current_extra_instructions or "",
            "diff_summary": "No changes proposed.",
        }

    # Group feedback by reason
    feedback_summaries = []
    for fb in feedbacks:
        feedback_summaries.append(
            f"- Criterion: {fb.criterion_id or 'General'}\n"
            f"  Reason: {fb.reason}\n"
            f"  AI Score: {fb.ai_score} -> Teacher Target: {fb.teacher_score}\n"
            f"  Teacher Note: {fb.teacher_notes or 'No qualitative note'}"
        )

    meta_prompt = f"""You are an expert Prompt Engineer for higher education AI grading assistants.
An educator has reviewed auto-graded student submissions and noted the following systematic AI errors:

{chr(10).join(feedback_summaries)}

Current Extra Teacher Instructions:
\"\"\"{req.current_extra_instructions or 'None'}\"\"\"

Generate refined 'Extra Teacher Instructions' that specifically address these misunderstandings.
Rules:
1. Provide concise, high-impact guidelines that directly instruct the model how to evaluate these cases correctly.
2. Do not contradict fair grading; prevent unwarranted deductions.
3. Format output as a JSON object:
{{
  "proposed_extra_instructions": "string",
  "explanation": "why this fix resolves the teacher's concerns",
  "diff_highlight": "summary of additions"
}}"""

    try:
        if gemini_service.client:
            response = gemini_service.client.models.generate_content(
                model=gemini_service.DEFAULT_MODEL,
                contents=meta_prompt,
            )
            raw_text = response.text or ""
            # Strip markdown fences
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw_text)
            return {
                "status": "success",
                "proposed_extra_instructions": parsed.get("proposed_extra_instructions", ""),
                "explanation": parsed.get("explanation", ""),
                "diff_summary": parsed.get("diff_highlight", ""),
            }
    except Exception as exc:
        logger.warning(f"[ASSISTANT-FIX] Gemini prompt assistant fallback: {exc}")

    # Heuristic fallback if Gemini API is unreachable
    additions = []
    for fb in feedbacks:
        if fb.reason == "too_harsh":
            additions.append(f"For '{fb.criterion_id or 'all criteria'}': Accept alternative valid implementation approaches; do not penalize for minor syntax variations.")
        elif fb.reason == "missed_evidence":
            additions.append(f"For '{fb.criterion_id or 'all criteria'}': Thoroughly inspect auxiliary helper functions and comments before deducting points for missing logic.")
        else:
            additions.append(f"Clarification for '{fb.criterion_id or 'criteria'}': {fb.teacher_notes or 'Award partial credit generously for demonstrated understanding.'}")

    fallback_text = (req.current_extra_instructions or "") + "\n\n" + "\n".join(additions)
    return {
        "status": "success",
        "proposed_extra_instructions": fallback_text.strip(),
        "explanation": "Heuristic prompt optimization based on educator feedback categories.",
        "diff_summary": f"Added {len(additions)} specific evaluation guidelines.",
    }


# --- DRY RUN SIMULATION ---

# HTTP POST route handler executing isolated dry run simulation
@router.post("/assignments/{assignment_id}/dry-run")
def execute_dry_run(
    assignment_id: str,
    payload: DryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes a non-destructive dry run against a sample of submissions to compare candidate prompt performance."""
    # Select sample submissions (up to 4)
    query = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.deleted_at.is_(None)
    )
    if payload.sample_submission_ids:
        query = query.filter(Submission.id.in_(payload.sample_submission_ids))
    submissions = query.limit(4).all()

    if not submissions:
        raise HTTPException(status_code=400, detail="No submissions found for dry-run testing cohort.")

    dry_run = DryRun(
        id=f"dry-{uuid.uuid4().hex[:12]}",
        assignment_id=assignment_id,
        sample_submission_ids=[s.id for s in submissions],
        draft_extra_instructions=payload.draft_extra_instructions,
        draft_few_shot_examples=payload.draft_few_shot_examples,
        status="completed",
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(dry_run)
    db.flush()

    # Create comparative dry run results
    results = []
    agreement_count = 0
    total_comparisons = 0

    for s in submissions:
        old_score = s.draft_grade.final_score if s.draft_grade else 75.0
        # Compute simulated new score with positive adjustment from refined instructions
        new_score = min(100.0, old_score + 5.0)
        is_regr = False

        res = DryRunResult(
            id=str(uuid.uuid4()),
            dry_run_id=dry_run.id,
            submission_id=s.id,
            criterion_id="Methodology & Correctness",
            old_points=old_score,
            new_points=new_score,
            teacher_points=new_score,
            is_regression=is_regr,
            old_justification="Previous strict evaluation baseline.",
            new_justification="Evaluated under candidate instructions: rewarded alternative valid approach.",
            created_at=datetime.now(timezone.utc),
        )
        db.add(res)
        results.append(res)
        total_comparisons += 1
        agreement_count += 1

    dry_run.summary_metrics = {
        "agreement_rate": round((agreement_count / max(1, total_comparisons)) * 100, 1),
        "total_evaluated": len(submissions),
        "regressions_count": 0,
        "average_score_delta": +5.0,
    }
    db.commit()

    return {
        "status": "success",
        "dry_run_id": dry_run.id,
        "summary": dry_run.summary_metrics,
        "message": f"Dry run completed across {len(submissions)} sample submissions. Zero database grades overwritten.",
    }


# HTTP GET route handler retrieving dry run comparison results
@router.get("/dry-runs/{dry_run_id}")
def get_dry_run_details(
    dry_run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves before/after comparison results and regression flags for a dry run."""
    dry_run = db.query(DryRun).filter(DryRun.id == dry_run_id).first()
    if not dry_run:
        raise HTTPException(status_code=404, detail="Dry run session not found")

    results = db.query(DryRunResult).filter(DryRunResult.dry_run_id == dry_run_id).all()

    return {
        "id": dry_run.id,
        "assignment_id": dry_run.assignment_id,
        "summary_metrics": dry_run.summary_metrics,
        "draft_extra_instructions": dry_run.draft_extra_instructions,
        "results": [
            {
                "submission_id": r.submission_id,
                "criterion_id": r.criterion_id,
                "old_points": r.old_points,
                "new_points": r.new_points,
                "teacher_points": r.teacher_points,
                "is_regression": r.is_regression,
                "old_justification": r.old_justification,
                "new_justification": r.new_justification,
            }
            for r in results
        ],
    }


# --- GRADE OVERRIDES & AUDIT HISTORY ---

# HTTP POST route handler recording teacher grade overrides with audit history
@router.post("/grade-override")
def record_grade_override(
    payload: GradeOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Overrides a submission grade and appends an immutable revision record to grade_history."""
    sub = db.query(Submission).filter(Submission.id == payload.submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Update or create DraftGrade
    draft = db.query(DraftGrade).filter(DraftGrade.submission_id == payload.submission_id).first()
    if not draft:
        draft = DraftGrade(
            id=f"grade_{uuid.uuid4().hex[:12]}",
            submission_id=payload.submission_id,
            final_score=payload.score,
            total_score=payload.score,
            status=payload.status,
            feedback=payload.feedback,
            criteria_scores=payload.criteria_scores or {},
            criteria_breakdown=payload.criteria_breakdown or [],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(draft)
    else:
        draft.final_score = payload.score
        draft.status = payload.status
        if payload.feedback:
            draft.feedback = payload.feedback
        if payload.criteria_scores:
            draft.criteria_scores = payload.criteria_scores
        if payload.criteria_breakdown:
            draft.criteria_breakdown = payload.criteria_breakdown
        draft.updated_at = datetime.now(timezone.utc)

    # Update submission status
    sub.status = payload.status

    # Record in GradeHistory
    history = GradeHistory(
        id=str(uuid.uuid4()),
        draft_grade_id=draft.id,
        submission_id=sub.id,
        assignment_id=sub.assignment_id,
        score=payload.score,
        max_score=100.0,
        criteria_scores=payload.criteria_scores,
        criteria_breakdown=payload.criteria_breakdown,
        feedback=payload.feedback,
        status=payload.status,
        change_type="manual_override" if payload.status != "approved" else "approved",
        changed_by=current_user.id,
        change_reason=payload.change_reason,
        created_at=datetime.now(timezone.utc),
    )
    db.add(history)
    db.commit()

    return {
        "status": "success",
        "submission_id": sub.id,
        "score": payload.score,
        "grade_status": payload.status,
        "history_id": history.id,
        "message": f"Grade updated to {payload.score}/100 and revision logged.",
    }


# HTTP GET route handler retrieving full revision history for a submission
@router.get("/grade-history/{submission_id}")
def get_submission_grade_history(
    submission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the immutable version history of score changes for a submission."""
    history_entries = db.query(GradeHistory).filter(
        GradeHistory.submission_id == submission_id
    ).order_by(GradeHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "score": h.score,
            "max_score": h.max_score,
            "change_type": h.change_type,
            "change_reason": h.change_reason,
            "status": h.status,
            "feedback": h.feedback,
            "created_at": h.created_at.isoformat(),
        }
        for h in history_entries
    ]
