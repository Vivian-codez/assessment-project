"""Batch Job Dispatcher and Progress Polling API endpoints."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger
from app.models.batch_job import BatchJob
from app.models.submission import Submission
from app.schemas.job import BatchEvaluationRequest, BatchJobResponse
from app.workers.evaluation_tasks import evaluate_batch_task, run_evaluation_batch_logic

router = APIRouter(tags=["Batch Jobs & Worker Tasks"])


@router.post("/assignments/{assignment_id}/evaluate-batch", response_model=BatchJobResponse)
@router.post("/assignments/{assignment_id}/evaluate", response_model=BatchJobResponse)
def trigger_batch_evaluation(
    assignment_id: str,
    payload: BatchEvaluationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Triggers background AI evaluation and similarity checks for batch submissions.

    Queues in Celery + Redis, with seamless background fallback if Celery
    broker is offline.
    """
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    submission_count = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()
    if submission_count == 0:
        try:
            from app.core.supabase import supabase
            sb_res = supabase.table("submissions").select("id", count="exact").eq("assignment_id", assignment_id).execute()
            if sb_res.count:
                submission_count = sb_res.count
        except Exception:
            pass

    job = BatchJob(
        id=job_id,
        assignment_id=assignment_id,
        status="queued",
        progress_pct=0.0,
        total_items=submission_count,
        processed_items=0,
    )
    db.add(job)
    db.commit()

    # Attempt Celery task queuing if active workers exist
    dispatched_celery = False
    try:
        from app.workers.celery_app import celery_app
        insp = celery_app.control.inspect(timeout=0.2)
        active_workers = insp.ping() if insp else None
        if active_workers:
            evaluate_batch_task.delay(
                job_id=job_id,
                assignment_id=assignment_id,
                submission_ids=payload.submission_ids,
                rubric_id=payload.rubric_id,
                similarity_threshold=payload.similarity_threshold,
            )
            dispatched_celery = True
            logger.info(f"Dispatched Celery task for batch job {job_id} to workers: {list(active_workers.keys())}")
        else:
            logger.info("No active Celery workers found; running via FastAPI BackgroundTasks.")
    except Exception as e:
        logger.warning(f"Celery check/dispatch failed: {e}. Executing via FastAPI background task.")

    if not dispatched_celery:
        # Fallback to FastAPI async background task for local/offline run
        background_tasks.add_task(
            run_evaluation_batch_logic,
            job_id=job_id,
            assignment_id=assignment_id,
            submission_ids=payload.submission_ids,
            rubric_id=payload.rubric_id,
            similarity_threshold=payload.similarity_threshold,
            title=payload.title,
            reference_assignment_text=payload.reference_assignment_text,
        )

    return BatchJobResponse(
        job_id=job_id,
        status="queued",
        progress_pct=0.0,
        total_items=submission_count,
        processed_items=0,
        similarity_flags=0,
        ready_for_review=0,
    )


@router.post("/evaluate", response_model=BatchJobResponse)
def trigger_evaluate_direct(
    payload: BatchEvaluationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Global evaluation trigger endpoint (/api/v1/evaluate)."""
    target_id = payload.assignment_id
    if not target_id:
        # Fallback to first available assignment
        from app.models.assignment import Assignment
        first_assign = db.query(Assignment).first()
        target_id = first_assign.id if first_assign else f"assign_{uuid.uuid4().hex[:12]}"

    return trigger_batch_evaluation(
        assignment_id=target_id,
        payload=payload,
        background_tasks=background_tasks,
        db=db,
    )


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll background batch processing progress (0-100%)."""
    job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")

    meta = job.meta_info or {}
    return BatchJobResponse(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        total_items=job.total_items,
        processed_items=job.processed_items,
        similarity_flags=meta.get("similarity_flags", 0),
        ready_for_review=meta.get("ready_for_review", job.processed_items),
        error_message=job.error_message,
    )


@router.get("/assignments/{assignment_id}/active-job", response_model=Optional[BatchJobResponse])
def get_active_assignment_job(assignment_id: str, db: Session = Depends(get_db)):
    """Check if an assignment currently has an evaluation job in process."""
    job = (
        db.query(BatchJob)
        .filter(BatchJob.assignment_id == assignment_id, BatchJob.status.in_(["queued", "processing"]))
        .order_by(BatchJob.created_at.desc())
        .first()
    )
    if not job:
        return None

    meta = job.meta_info or {}
    return BatchJobResponse(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        total_items=job.total_items,
        processed_items=job.processed_items,
        similarity_flags=meta.get("similarity_flags", 0),
        ready_for_review=meta.get("ready_for_review", job.processed_items),
        error_message=job.error_message,
    )

