"""Batch Job Dispatcher and Progress Polling API endpoints."""

import uuid
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
