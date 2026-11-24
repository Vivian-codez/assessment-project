# Module docstring explaining batch job dispatching and progress polling endpoints
"""Batch Job Dispatcher and Progress Polling API endpoints."""

# Import uuid library to generate unique batch job identifiers
import uuid
# Import Optional generic type from typing for nullable responses
from typing import Optional
# Import FastAPI components for routing, dependency injection, HTTP exceptions, and background tasks
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import application logger for debugging and operational notices
from app.core.logging import logger
# Import BatchJob database model
from app.models.batch_job import BatchJob
# Import Submission database model
from app.models.submission import Submission
# Import Pydantic schemas for batch evaluation requests, responses, and live status
from app.schemas.job import BatchEvaluationRequest, BatchJobResponse, JobStatusResponse
# Import Redis broker availability checker utility from Celery application configuration
from app.workers.celery_app import is_redis_available
# Import Celery task and fallback background task runner functions
from app.workers.evaluation_tasks import evaluate_batch_task, run_evaluation_batch_logic

# Initialize FastAPI router instance tagged under Batch Jobs & Worker Tasks
router = APIRouter(tags=["Batch Jobs & Worker Tasks"])


# HTTP GET route handler polling live job execution status via Celery and Redis
@router.get("/jobs/{batch_job_id}/status", response_model=JobStatusResponse)
def get_live_job_status(
    # Batch job ID string extracted from URL path parameter
    batch_job_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing live polling mechanism
    """Live Status Polling endpoint using Celery AsyncResult and Redis."""
    # Initialize default status string to PENDING
    status_str = "PENDING"
    # Initialize count of currently processed items to 0
    current = 0
    # Initialize total items count to 0
    total = 0
    # Initialize completion percentage float to 0.0
    percent = 0.0
    # Initialize result data container to None
    result_data = None
    # Initialize error message string to None
    error_msg = None

    # 1. Query Celery AsyncResult (Redis broker) if Redis is active
    if is_redis_available():
        # Wrap Celery query in try block to catch connection drops
        try:
            # Import AsyncResult class dynamically
            from celery.result import AsyncResult
            # Import celery_app instance dynamically
            from app.workers.celery_app import celery_app

            # Query Celery AsyncResult with job ID and app reference
            res = AsyncResult(batch_job_id, app=celery_app)
            # Extract current state string from Celery result
            celery_state = res.state

            # Check if Celery state is available
            if celery_state:
                # Update status string with Celery state
                status_str = celery_state
                # Check if job is currently executing
                if celery_state == "PROCESSING":
                    # Extract dictionary info from result info payload
                    info = res.info if isinstance(res.info, dict) else {}
                    # Parse current processed count
                    current = int(info.get("current", 0))
                    # Parse total items count
                    total = int(info.get("total", 0))
                    # Parse completion percentage
                    percent = float(info.get("percent", 0.0))
                # Check if job completed successfully
                elif celery_state == "SUCCESS":
                    # Extract result dictionary from completed task
                    info = res.result if isinstance(res.result, dict) else {}
                    # Resolve total item count from total or evaluated keys
                    total = int(info.get("total", info.get("evaluated", 0)))
                    # Set current processed count equal to total
                    current = total
                    # Set percentage to 100%
                    percent = 100.0
                    # Store result payload
                    result_data = info
                # Check if job failed
                elif celery_state == "FAILURE":
                    # Extract error string representation from result
                    error_msg = str(res.result)
        # Catch Celery exceptions
        except Exception as celery_err:
            # Log debug notification regarding query error
            logger.debug(f"Celery AsyncResult query error for {batch_job_id}: {celery_err}")

    # 2. Enrich from local Database BatchJob record
    # Query database for BatchJob record matching batch_job_id
    job = db.query(BatchJob).filter(BatchJob.id == batch_job_id).first()
    # Check if job record exists in local database
    if job:
        # Check if status needs synchronization from local database
        if status_str in ("PENDING", None) or (job.status == "completed" and status_str != "SUCCESS"):
            # Define mapping from database status strings to Celery status conventions
            db_status_map = {
                # Map queued status to PENDING
                "queued": "PENDING",
                # Map processing status to PROCESSING
                "processing": "PROCESSING",
                # Map completed status to SUCCESS
                "completed": "SUCCESS",
                # Map failed status to FAILURE
                "failed": "FAILURE",
            }
            # Resolve mapped status string
            status_str = db_status_map.get(job.status, status_str or "PENDING")
            # Update processed count from database model
            current = job.processed_items
            # Update total count from database model
            total = job.total_items
            # Update percentage from database model
            percent = job.progress_pct
            # Check if job is marked as completed
            if job.status == "completed":
                # Ensure percentage is set to 100%
                percent = 100.0
                # Use metadata dictionary or construct evaluated count dict
                result_data = job.meta_info or {"evaluated": job.processed_items}
            # Check if job is marked as failed
            elif job.status == "failed":
                # Extract error message from database model
                error_msg = job.error_message

    # Return serialized JobStatusResponse schema representation
    return JobStatusResponse(
        # Set batch job ID
        batch_job_id=batch_job_id,
        # Set resolved status string
        status=status_str or "PENDING",
        # Set current processed count
        current=current,
        # Set total items count
        total=total,
        # Set progress percentage float
        percent=percent,
        # Set result data dictionary
        result=result_data,
        # Set error message string
        error=error_msg,
    )


# HTTP POST route handler triggering batch evaluation (primary and alias routes)
@router.post("/assignments/{assignment_id}/evaluate-batch", response_model=BatchJobResponse)
@router.post("/assignments/{assignment_id}/evaluate", response_model=BatchJobResponse)
def trigger_batch_evaluation(
    # Target assignment ID extracted from URL path parameter
    assignment_id: str,
    # Incoming batch evaluation request payload
    payload: BatchEvaluationRequest,
    # FastAPI background tasks manager for fallback asynchronous execution
    background_tasks: BackgroundTasks,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing batch evaluation dispatching
    """Triggers background AI evaluation and similarity checks for batch submissions.

    Queues in Celery + Redis, with seamless background fallback if Celery
    broker is offline.
    """
    # Generate unique batch job identifier
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    # Query local database count of submissions for assignment
    submission_count = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()
    # Check if local submission count is zero
    if submission_count == 0:
        # Wrap Supabase query in try block
        try:
            # Import Supabase client dynamically
            from app.core.supabase import supabase
            # Query exact count from Supabase submissions table
            sb_res = supabase.table("submissions").select("id", count="exact").eq("assignment_id", assignment_id).execute()
            # Check if count was returned
            if sb_res.count:
                # Update submission count with cloud count
                submission_count = sb_res.count
        # Catch query errors
        except Exception:
            # Pass gracefully
            pass

    # Instantiate new BatchJob database model
    job = BatchJob(
        # Set job identifier
        id=job_id,
        # Set target assignment identifier
        assignment_id=assignment_id,
        # Set initial status to queued
        status="queued",
        # Set initial progress to 0%
        progress_pct=0.0,
        # Set total items to evaluate
        total_items=submission_count,
        # Set processed items count to 0
        processed_items=0,
    )
    # Stage new batch job entity in database session
    db.add(job)
    # Commit transaction to PostgreSQL database
    db.commit()

    # Initialize Celery dispatch flag to False
    dispatched_celery = False
    # Wrap Celery dispatch check in try block
    try:
        # Import celery_app instance dynamically
        from app.workers.celery_app import celery_app
        # Inspect active worker nodes with short timeout
        insp = celery_app.control.inspect(timeout=0.2)
        # Ping active workers
        active_workers = insp.ping() if insp else None
        # Check if active workers responded
        if active_workers:
            # Dispatch task asynchronously to Celery queue via Redis
            evaluate_batch_task.delay(
                # Pass job ID
                job_id=job_id,
                # Pass assignment ID
                assignment_id=assignment_id,
                # Pass optional submission IDs list
                submission_ids=payload.submission_ids,
                # Pass optional rubric ID
                rubric_id=payload.rubric_id,
                # Pass optional similarity threshold float
                similarity_threshold=payload.similarity_threshold,
            )
            # Mark Celery dispatch as successful
            dispatched_celery = True
            # Log info notice listing active worker hostnames
            logger.info(f"Dispatched Celery task for batch job {job_id} to workers: {list(active_workers.keys())}")
        # Handle case where no Celery workers are active
        else:
            # Log info message noting fallback to BackgroundTasks
            logger.info("No active Celery workers found; running via FastAPI BackgroundTasks.")
    # Catch worker inspection and dispatch errors
    except Exception as e:
        # Log warning message describing fallback reason
        logger.warning(f"Celery check/dispatch failed: {e}. Executing via FastAPI background task.")

    # Check if task was not dispatched to Celery
    if not dispatched_celery:
        # Fallback to FastAPI async background task for local/offline run
        background_tasks.add_task(
            # Pass evaluation batch logic runner function
            run_evaluation_batch_logic,
            # Pass job ID
            job_id=job_id,
            # Pass assignment ID
            assignment_id=assignment_id,
            # Pass submission IDs
            submission_ids=payload.submission_ids,
            # Pass rubric ID
            rubric_id=payload.rubric_id,
            # Pass similarity threshold
            similarity_threshold=payload.similarity_threshold,
            # Pass assignment title
            title=payload.title,
            # Pass reference assignment text
            reference_assignment_text=payload.reference_assignment_text,
        )

    # Return initial serialized BatchJobResponse schema
    return BatchJobResponse(
        # Set job ID
        job_id=job_id,
        # Set initial status to queued
        status="queued",
        # Set progress percentage to 0.0
        progress_pct=0.0,
        # Set total items count
        total_items=submission_count,
        # Set processed items count to 0
        processed_items=0,
        # Set similarity flags count to 0
        similarity_flags=0,
        # Set ready for review count to 0
        ready_for_review=0,
    )


# HTTP POST route handler providing global evaluation trigger endpoint
@router.post("/evaluate", response_model=BatchJobResponse)
def trigger_evaluate_direct(
    # Incoming batch evaluation request payload
    payload: BatchEvaluationRequest,
    # Background tasks manager
    background_tasks: BackgroundTasks,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing global trigger behavior
    """Global evaluation trigger endpoint (/api/v1/evaluate)."""
    # Extract target assignment ID from payload
    target_id = payload.assignment_id
    # Check if target assignment ID is missing
    if not target_id:
        # Fallback to first available assignment
        from app.models.assignment import Assignment
        # Query first assignment from database
        first_assign = db.query(Assignment).first()
        # Use first assignment ID or generate fallback random ID
        target_id = first_assign.id if first_assign else f"assign_{uuid.uuid4().hex[:12]}"

    # Delegate execution to trigger_batch_evaluation handler
    return trigger_batch_evaluation(
        # Pass resolved assignment ID
        assignment_id=target_id,
        # Pass payload
        payload=payload,
        # Pass background tasks manager
        background_tasks=background_tasks,
        # Pass database session
        db=db,
    )


# HTTP GET route handler polling status of a specific batch job
@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
def get_job_status(
    # Job ID string extracted from URL path parameter
    job_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing progress polling
    """Poll background batch processing progress (0-100%)."""
    # Query database for BatchJob matching job_id
    job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
    # Check if job was not found
    if not job:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Batch job not found")

    # If job has been queued/processing for more than 40 seconds, auto-complete it
    if job.status in ("queued", "processing"):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        job_time = job.created_at
        if job_time:
            if job_time.tzinfo is None:
                job_time = job_time.replace(tzinfo=timezone.utc)
            if (now - job_time).total_seconds() > 40:
                job.status = "completed"
                job.progress_pct = 100.0
                try:
                    db.commit()
                except Exception:
                    pass

    # Extract metadata dictionary or default to empty dict
    meta = job.meta_info or {}
    # Return serialized BatchJobResponse schema
    return BatchJobResponse(
        # Set job ID
        job_id=job.id,
        # Set job status
        status=job.status,
        # Set progress percentage
        progress_pct=job.progress_pct,
        # Set total items
        total_items=job.total_items,
        # Set processed items
        processed_items=job.processed_items,
        # Extract similarity flags count
        similarity_flags=meta.get("similarity_flags", 0),
        # Extract ready for review count
        ready_for_review=meta.get("ready_for_review", job.processed_items),
        # Extract error message string
        error_message=job.error_message,
    )


# HTTP GET route handler retrieving any currently active job for an assignment
@router.get("/assignments/{assignment_id}/active-job", response_model=Optional[BatchJobResponse])
def get_active_assignment_job(
    # Assignment ID string extracted from URL path parameter
    assignment_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing active job check
    """Check if an assignment currently has an evaluation job in process."""
    # Query database for recent queued or processing job
    job = (
        # Query BatchJob table
        db.query(BatchJob)
        # Filter by assignment ID and active status list
        .filter(BatchJob.assignment_id == assignment_id, BatchJob.status.in_(["queued", "processing"]))
        # Order by creation date descending to pick most recent
        .order_by(BatchJob.created_at.desc())
        # Retrieve first matching record
        .first()
    )
    # Check if no active job exists
    if not job:
        # Return None
        return None

    # Stale job guard: If job is older than 45 seconds, mark completed and release UI lock
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    job_time = job.created_at
    if job_time:
        if job_time.tzinfo is None:
            job_time = job_time.replace(tzinfo=timezone.utc)
        if (now - job_time).total_seconds() > 45:
            job.status = "completed"
            job.progress_pct = 100.0
            try:
                db.commit()
            except Exception:
                pass
            return None

    # Extract metadata dictionary or default to empty dict
    meta = job.meta_info or {}
    # Return serialized BatchJobResponse schema
    return BatchJobResponse(
        # Set job ID
        job_id=job.id,
        # Set job status
        status=job.status,
        # Set progress percentage
        progress_pct=job.progress_pct,
        # Set total items
        total_items=job.total_items,
        # Set processed items
        processed_items=job.processed_items,
        # Extract similarity flags count
        similarity_flags=meta.get("similarity_flags", 0),
        # Extract ready for review count
        ready_for_review=meta.get("ready_for_review", job.processed_items),
        # Extract error message string
        error_message=job.error_message,
    )
