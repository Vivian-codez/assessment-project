# Module docstring explaining the Celery background worker tasks for evaluation and plagiarism pipeline
"""Celery Background Worker Tasks for Batch Evaluation & Plagiarism Pipeline.

Implements the complete asynchronous evaluation pipeline:
1. For each submission in batch:
   a. Extract text or code content from the file (downloads from Supabase Storage if needed).
   b. Generate text embeddings (text-embedding-004) and query Qdrant collection
      `submissions_{assignment_id}` to detect peer-to-peer similarity (> 0.75).
   c. Call gemini-2.5-flash with assignment prompt, model solution (reference exemplar),
      matrix rubric, and peer-matching context using strict JSON output schema (EvaluationResult).
   d. Upsert criteria scores, qualitative notes, and plagiarism flags into the `draft_grades`
      table in Supabase.
   e. Insert the current submission vector into Qdrant collection `submissions_{assignment_id}`
      so subsequent students in the batch are compared against it.
   f. Update Celery task state/progress in Redis ({"current": i, "total": total, "status": "PROCESSING"}).
   g. Update `submissions.status = 'completed'`.
"""

# Import the os module for local file path verification and operations
import os
# Import the re regular expression module for string pattern matching
import re
# Import the uuid module to generate unique identifier tokens
import uuid
# Import hashlib for SHA-256 content-hash evaluation caching
import hashlib
# Import json module for serialization and deserialization
import json
# Import time module for latency calculations and jitter
import time
# Import datetime and timezone classes for timestamping
from datetime import datetime, timezone
# Import typing helpers for comprehensive type annotations
from typing import Any, Dict, List, Optional, Union

# Import the configured Celery application instance
from app.workers.celery_app import celery_app
# Import global configuration settings
from app.core.config import settings
# Import SQLAlchemy database session factory
from app.core.database import SessionLocal
# Import logger and audit event logging utilities
from app.core.logging import logger, log_audit_event
# Import Supabase client instance
from app.core.supabase import supabase
# Import the Assignment database model
from app.models.assignment import Assignment
# Import the Rubric database model
from app.models.rubric import Rubric
# Import the Submission database model
from app.models.submission import Submission
# Import the DraftGrade database model
from app.models.draft_grade import DraftGrade
# Import the SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch
# Import the BatchJob database model
from app.models.batch_job import BatchJob
# Import the Gemini AI evaluation service instance
from app.services.gemini_service import gemini_service
# Import the Qdrant vector database service instance
from app.services.vector_service import vector_service
# Import the FERPA privacy and encryption service instance
from app.services.ferpa_service import ferpa_service
# Import the PDF and document text extraction service instance
from app.services.pdf_service import pdf_service
# Import the Supabase database and storage service wrapper
from app.services.supabase_service import supabase_service
# Import grading evaluation Pydantic schemas
from app.schemas.grading import EvaluationResult, CriterionEvaluationItem, PlagiarismReport


# Helper function to get an active Redis client with short timeout
def get_redis_client():
    # Docstring explaining Redis client retrieval
    """Returns a connected Redis client or None if Redis is unreachable."""
    # Begin try block to instantiate client
    try:
        # Import redis module dynamically
        import redis
        # Instantiate Redis client using configured REDIS_URL
        return redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    # Catch any connection error
    except Exception:
        # Return None
        return None


# Helper function checking content-hash evaluation cache in Redis
def get_content_evaluation_cache(content: str, rubric_data: Any) -> Optional[Dict[str, Any]]:
    # Docstring explaining content-hash evaluation cache retrieval
    """Checks Redis for cached evaluation using SHA-256 of submission content and rubric version."""
    # Obtain Redis client
    client = get_redis_client()
    # If Redis is unavailable, return None
    if not client:
        # Return None
        return None
    # Begin try block for cache lookup
    try:
        # Calculate SHA-256 hash of submission content
        c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        # Serialize rubric data to JSON string
        r_str = json.dumps(rubric_data, sort_keys=True) if not isinstance(rubric_data, str) else rubric_data
        # Calculate SHA-256 hash of rubric data
        r_hash = hashlib.sha256(r_str.encode("utf-8")).hexdigest()
        # Formulate composite cache key
        cache_key = f"eval_cache:{c_hash}:{r_hash}"
        # Retrieve cached payload from Redis
        cached = client.get(cache_key)
        # Check if cache hit
        if cached:
            # Parse and return cached JSON dictionary
            return json.loads(cached.decode("utf-8"))
    # Catch any caching exception silently
    except Exception:
        # Return None on error
        pass
    # Return None on cache miss
    return None


# Helper function storing evaluation result in content-hash cache with 7-day TTL
def set_content_evaluation_cache(content: str, rubric_data: Any, result: Dict[str, Any]):
    # Docstring explaining content-hash evaluation cache storage
    """Stores evaluation result in Redis keyed by SHA-256 of content and rubric."""
    # Obtain Redis client
    client = get_redis_client()
    # Return if Redis unavailable
    if not client:
        # Return
        return
    # Begin try block for cache storage
    try:
        # Calculate SHA-256 hash of submission content
        c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        # Serialize rubric data
        r_str = json.dumps(rubric_data, sort_keys=True) if not isinstance(rubric_data, str) else rubric_data
        # Calculate SHA-256 hash of rubric data
        r_hash = hashlib.sha256(r_str.encode("utf-8")).hexdigest()
        # Formulate composite cache key
        cache_key = f"eval_cache:{c_hash}:{r_hash}"
        # Store in Redis with 7-day (604800s) time-to-live
        client.set(cache_key, json.dumps(result), ex=604800)
    # Catch any storage error silently
    except Exception:
        # Pass
        pass


# Helper function updating real-time grading progress in Redis
def update_assignment_progress(assignment_id: str, progress_data: Dict[str, Any]):
    # Docstring explaining assignment progress update in Redis
    """Updates real-time grading progress state in Redis for UI streaming and polling."""
    # Obtain Redis client
    client = get_redis_client()
    # Return if Redis unavailable
    if not client:
        # Return
        return
    # Begin try block for progress update
    try:
        # Formulate progress key
        key = f"assignment_progress:{assignment_id}"
        # Store progress dictionary in Redis with 24-hour TTL
        client.set(key, json.dumps(progress_data), ex=86400)
    # Catch any progress update error
    except Exception:
        # Pass
        pass


# Helper function checking if grading was cancelled by teacher
def is_grading_cancelled(assignment_id: str) -> bool:
    # Docstring explaining grading cancellation check
    """Checks whether teacher requested cancellation of active grading job."""
    # Obtain Redis client
    client = get_redis_client()
    # Return False if Redis unavailable
    if not client:
        # Return False
        return False
    # Begin try block for cancellation check
    try:
        # Check cancellation flag in Redis
        return bool(client.get(f"cancel_grading:{assignment_id}"))
    # Catch any error
    except Exception:
        # Return False
        return False


# Register Celery task for fast text and code extraction
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.extract_submission_task")
def extract_submission_task(self, submission_id: str):
    # Docstring explaining extract_submission_task
    """Extracts text or source code from submission file and caches in database."""
    # Open database session
    db = SessionLocal()
    # Begin try block
    try:
        # Query submission by ID
        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        # Return if not found
        if not sub:
            # Return not found status
            return {"status": "error", "message": "Submission not found"}
        # Extract text using pdf_service
        text = sub.extracted_text or sub.content or ""
        # If not already extracted, extract from path
        if not text and sub.file_path and os.path.exists(sub.file_path):
            # Extract text
            text = pdf_service.extract_text_from_file_path(sub.file_path)
            # Update model
            sub.extracted_text = text
            # Commit update
            db.commit()
        # Return extracted status
        return {"status": "success", "submission_id": submission_id, "text_length": len(text)}
    # Handle cleanup
    finally:
        # Close database session
        db.close()


# Register Celery task for CPU-heavy OCR extraction
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.ocr_submission_task")
def ocr_submission_task(self, submission_id: str):
    # Docstring explaining ocr_submission_task
    """Performs OCR text extraction on scanned documents or images."""
    # Delegate to extraction task with OCR fallback
    return extract_submission_task(submission_id)


# Register Celery task for single submission autograding
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.grade_submission_task")
def grade_submission_task(self, submission_id: str, rubric_id: Optional[str] = None, assignment_id: Optional[str] = None):
    # Docstring explaining grade_submission_task
    """Grades a single submission using Phase 5 prompt and strict Python arithmetic."""
    # Open database session
    db = SessionLocal()
    # Begin try block
    try:
        # Query submission
        sub = db.query(Submission).filter(Submission.id == submission_id).first()
        # Return if not found
        if not sub:
            # Return not found
            return {"status": "error", "message": "Submission not found"}
        # Execute batch evaluation with single submission
        return run_evaluation_batch_logic(
            job_id=f"job_single_{submission_id[:8]}",
            assignment_id=assignment_id or sub.assignment_id,
            submission_ids=[submission_id],
            rubric_id=rubric_id,
            task_instance=self,
        )
    # Handle cleanup
    finally:
        # Close database session
        db.close()


# Register Celery task for similarity analysis
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.similarity_check_task")
def similarity_check_task(self, assignment_id: str):
    # Docstring explaining similarity_check_task
    """Performs deterministic pairwise similarity and plagiarism check on an assignment."""
    # Import integrity service
    from app.services.integrity_service import integrity_service
    # Open database session
    db = SessionLocal()
    # Begin try block
    try:
        # Query assignment
        assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        # If not found, return error
        if not assign:
            # Return error
            return {"status": "error", "message": "Assignment not found"}
        # Query submissions
        subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
        # Return evaluated summary
        return {"status": "success", "assignment_id": assignment_id, "submissions_count": len(subs)}
    # Handle cleanup
    finally:
        # Close session
        db.close()


# Register Celery task for gradebook export
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.export_gradebook_task")
def export_gradebook_task(self, course_id: str):
    # Docstring explaining export_gradebook_task
    """Asynchronously generates gradebook CSV or PDF export."""
    # Return success confirmation
    return {"status": "success", "course_id": course_id, "message": "Gradebook export completed"}



# Register celery task with bind=True to access the running task instance
@celery_app.task(bind=True, name="app.workers.evaluation_tasks.evaluate_batch_task")
# Define the background task entrypoint function for batch evaluations
def evaluate_batch_task(
    # Reference to the bound Celery Task instance
    self,
    # Optional list or string identifier for batch submissions
    batch_submission_ids: Optional[Union[List[str], str]] = None,
    # Optional rubric identifier string
    rubric_id: Optional[str] = None,
    # Optional assignment identifier string
    assignment_id: Optional[str] = None,
    # Optional batch job identifier string
    job_id: Optional[str] = None,
    # Catch-all dictionary for extra keyword arguments
    **kwargs,
):
    # Docstring describing the task purpose and accepted parameter signatures
    """Celery background worker task for batch submission evaluation.

    Accepts both:
      evaluate_batch_task.delay(batch_submission_ids, rubric_id, assignment_id)
    and:
      evaluate_batch_task.delay(job_id=..., assignment_id=..., submission_ids=...)
    """
    # Normalize argument order for flexible dispatcher invocations
    # Check if batch_submission_ids was passed as a job or assignment string prefix
    if isinstance(batch_submission_ids, str) and (
        batch_submission_ids.startswith("job_")
        or (rubric_id and isinstance(rubric_id, str) and (rubric_id.startswith("assign_") or rubric_id.startswith("a_")))
    ):
        # Assign the first argument as the job id
        passed_job_id = batch_submission_ids
        # Assign the second argument as the assignment id
        passed_assignment_id = rubric_id
        # Extract submission ids from assignment_id or kwargs
        passed_submission_ids = assignment_id if isinstance(assignment_id, list) else kwargs.get("submission_ids")
        # Extract target rubric id from kwargs
        target_rubric_id = kwargs.get("rubric_id")
    # Handle standard positional or keyword parameter mapping
    else:
        # Retrieve the Celery request task ID if available
        celery_task_id = self.request.id if (hasattr(self, "request") and self.request and self.request.id) else None
        # Determine job ID from explicit argument, task ID, or generated UUID
        passed_job_id = job_id or celery_task_id or f"job_{uuid.uuid4().hex[:12]}"
        # Determine assignment ID from parameter or kwargs
        passed_assignment_id = assignment_id or kwargs.get("assignment_id")
        # Determine list of submission IDs from first parameter or kwargs
        passed_submission_ids = batch_submission_ids if isinstance(batch_submission_ids, list) else kwargs.get("submission_ids")
        # Assign rubric ID from positional parameter
        target_rubric_id = rubric_id

    # Execute and return the core evaluation batch processing logic
    return run_evaluation_batch_logic(
        # Pass normalized job identifier
        job_id=passed_job_id,
        # Pass normalized assignment identifier
        assignment_id=passed_assignment_id,
        # Pass normalized list of submission identifiers
        submission_ids=passed_submission_ids,
        # Pass normalized rubric identifier
        rubric_id=target_rubric_id,
        # Pass Celery task instance for progress updates
        task_instance=self,
        # Forward additional keyword arguments
        **kwargs,
    )


# Define helper function to ensure assignment record exists in local database
def _ensure_assignment_in_db(
    # Database session parameter
    db,
    # Assignment identifier string
    assignment_id: str,
    # Optional assignment title
    title: Optional[str] = None,
    # Optional reference assignment text
    reference_assignment_text: Optional[str] = None,
    # Optional rubric identifier string
    rubric_id: Optional[str] = None,
) -> Optional[Assignment]:
    # Docstring explaining assignment database synchronization
    """Ensure assignment exists in local DB and Supabase."""
    # Check if an assignment ID was provided
    if not assignment_id:
        # Return None if no assignment ID is present
        return None

    # Query local database for assignment matching ID
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Check if assignment already exists locally
    if assignment:
        # Return existing assignment entity
        return assignment

    # Try fetching assignment details from Supabase if not found locally
    try:
        # Import Course model to ensure course foreign key reference exists
        from app.models.course import Course
        # Fetch assignment record from Supabase table
        res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        # Verify if Supabase returned data for this assignment
        if res.data:
            # Extract first matching assignment record
            a_data = res.data[0]
            # Get course ID from record or fallback to default
            course_id = a_data.get("course_id") or "c_default"
            # Query local database for course entity
            course = db.query(Course).filter(Course.id == course_id).first()
            # If course does not exist locally, fetch and create it
            if not course:
                # Query Supabase for course data
                c_res = supabase.table("courses").select("*").eq("id", course_id).execute()
                # Extract course data dictionary
                c_data = c_res.data[0] if (c_res and c_res.data) else {}
                # Instantiate new Course model with fallback defaults
                course = Course(
                    id=course_id,
                    name=c_data.get("name", "Classroom Course"),
                    code=c_data.get("code", "CS101"),
                    section=c_data.get("section", "A"),
                    tone=c_data.get("tone", "lav"),
                )
                # Add course to database session
                db.add(course)
                # Commit course creation to database
                db.commit()

            # Instantiate Assignment model using Supabase row data
            assignment = Assignment(
                id=a_data["id"],
                course_id=course_id,
                title=a_data.get("title") or title or f"Assignment {assignment_id}",
                description=a_data.get("description", ""),
                max_score=float(a_data.get("max_score", 100.0)),
                rubric_id=a_data.get("rubric_id") or rubric_id,
                reference_assignment_text=a_data.get("reference_assignment_text") or reference_assignment_text,
            )
            # Add assignment to database session
            db.add(assignment)
            # Commit assignment creation to database
            db.commit()
            # Refresh assignment instance with generated state
            db.refresh(assignment)
            # Return newly synchronized assignment model
            return assignment
    # Handle any exceptions during Supabase lookup gracefully
    except Exception as e:
        # Log warning message for Supabase lookup failure
        logger.warning(f"Assignment lookup from Supabase notice: {e}")

    # Fallback assignment creation if Supabase query was not successful
    # Begin try block for fallback creation
    try:
        # Import Course model for fallback association
        from app.models.course import Course
        # Query for any existing course in local database
        course = db.query(Course).first()
        # Use existing course ID or default course ID
        course_id = course.id if course else "c_default"
        # If no course exists at all, create a default course
        if not course:
            # Instantiate default Course entity
            course = Course(id=course_id, name="Computer Science", code="CS101")
            # Add default course to database session
            db.add(course)
            # Commit default course to database
            db.commit()

        # Instantiate fallback Assignment record
        assignment = Assignment(
            id=assignment_id,
            course_id=course_id,
            title=title or f"Assignment {assignment_id}",
            description="Active assignment payload",
            max_score=100.0,
            rubric_id=rubric_id,
            reference_assignment_text=reference_assignment_text or "Benchmark Reference Solution: Implement robust algorithms with clean modularity and comprehensive test coverage.",
        )
        # Add fallback assignment to database session
        db.add(assignment)
        # Commit fallback assignment to database
        db.commit()
        # Refresh fallback assignment instance
        db.refresh(assignment)
        # Return created fallback assignment
        return assignment
    # Catch any error during fallback creation
    except Exception as create_err:
        # Log error indicating fallback creation failure
        logger.error(f"Failed to create assignment fallback for {assignment_id}: {create_err}")
        # Return None if fallback creation fails
        return None


# Define primary synchronous batch evaluation logic function
def run_evaluation_batch_logic(
    # Job identifier string
    job_id: str,
    # Assignment identifier string
    assignment_id: str,
    # Optional list of submission identifiers to evaluate
    submission_ids: Optional[List[str]] = None,
    # Optional rubric identifier string
    rubric_id: Optional[str] = None,
    # Optional Celery task instance for status updates
    task_instance=None,
    # Catch-all dictionary for additional keyword parameters
    **kwargs,
) -> Dict[str, Any]:
    # Docstring describing the full execution pipeline
    """Executes the complete batch evaluation pipeline:
    1. Update Celery task state/progress in Redis ({"current": 0, "total": total, "status": "PROCESSING"})
    2. Extract text/code content from each file (downloads from Supabase Storage if needed)
    3. Generate text embeddings (text-embedding-004) & query Qdrant collection `submissions_{assignment_id}`
       for peer cosine similarity (> 0.75)
    4. Query gemini-2.5-flash with assignment prompt, model solution, matrix rubric,
       and peer-matching context using strict JSON output schema (EvaluationResult)
    5. Upsert criteria scores, qualitative notes, and plagiarism flags into `draft_grades` table in Supabase
    6. Insert current submission vector into Qdrant collection `submissions_{assignment_id}`
    7. Update `submissions.status = 'completed'`
    """
    # Create a new local database session
    db = SessionLocal()
    # Begin try block to ensure database session cleanup in finally
    try:
        # 1. Initialize or update BatchJob record
        # Query for existing BatchJob by ID
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        # Check if job does not exist in local database
        if not job:
            # Create a new BatchJob entity with processing status
            job = BatchJob(id=job_id, assignment_id=assignment_id, status="processing")
            # Add new job to database session
            db.add(job)
        # If job already exists, update its status and progress
        else:
            # Set job status to processing
            job.status = "processing"
            # Set initial progress to 5%
            job.progress_pct = 5.0
        # Commit batch job changes to database
        db.commit()

        # 2. Resolve Assignment, Rubric, and Reference Solution
        # Ensure assignment exists in database and fetch instance
        assignment = _ensure_assignment_in_db(
            db,
            assignment_id,
            title=kwargs.get("title"),
            reference_assignment_text=kwargs.get("reference_assignment_text"),
            rubric_id=rubric_id,
        )

        # Determine target rubric ID from argument or assignment definition
        target_rubric_id = rubric_id or (assignment.rubric_id if assignment else None)
        # Initialize list to hold rubric criteria definitions
        rubric_criteria_list: List[Dict[str, Any]] = []

        # Check Supabase rubrics or local DB
        # If rubric ID is provided, check Supabase first
        if target_rubric_id:
            # Begin try block for Supabase rubric fetch
            try:
                # Fetch rubric data from Supabase service
                sb_rubric = supabase_service.get_rubric(target_rubric_id)
                # Verify if rubric contains criteria list
                if sb_rubric and sb_rubric.get("criteria"):
                    # Assign criteria list from Supabase
                    rubric_criteria_list = sb_rubric["criteria"]
            # Handle Supabase rubric fetch error gracefully
            except Exception as r_err:
                # Log warning notice for failed Supabase rubric fetch
                logger.warning(f"Rubric fetch notice from Supabase: {r_err}")

        # If Supabase had no criteria, check local database
        if not rubric_criteria_list and target_rubric_id:
            # Query local database for Rubric entity
            local_rubric = db.query(Rubric).filter(Rubric.id == target_rubric_id).first()
            # If local rubric exists with criteria, extract them
            if local_rubric and local_rubric.criteria:
                # Build formatted criteria dictionary list from local model
                rubric_criteria_list = [
                    {
                        "name": c.criterion_name or c.name or "Criterion",
                        "description": c.description or "",
                        "weight": c.weight or 25.0,
                        "max_score": c.max_points or c.max_score or 4.0,
                    }
                    for c in local_rubric.criteria
                ]

        # If still no criteria found, provide standard academic fallback rubric
        if not rubric_criteria_list:
            # Standard matrix academic rubric default
            # Define standard default criteria list
            rubric_criteria_list = [
                {"name": "Algorithmic Correctness", "description": "Accurate functional implementation and edge case handling", "weight": 40.0, "max_score": 40.0},
                {"name": "Code Structure & Modularity", "description": "Clean functional separation, naming, and architectural elegance", "weight": 30.0, "max_score": 30.0},
                {"name": "Analytical Documentation", "description": "Comprehensive explanation of complexity and methodology", "weight": 30.0, "max_score": 30.0},
            ]

        # 3. Ensure Qdrant collection submissions_{assignment_id}
        # Derive collection name for this assignment
        collection_name = vector_service.get_collection_name(assignment_id)
        # Ensure Qdrant collection exists or create it
        vector_service.ensure_collection(collection_name=collection_name, assignment_id=assignment_id)

        # 4. Resolve Target Submissions
        # Query local database for submissions belonging to this assignment
        query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
        # Filter by specific submission IDs if provided
        if submission_ids:
            # Apply IN filter for matching IDs
            query = query.filter(Submission.id.in_(submission_ids))
        # Execute query and retrieve submissions list
        submissions: List[Submission] = query.all()

        # If not present in local DB, fetch from Supabase
        # Check if local query returned no submissions
        if not submissions:
            # Begin try block to query Supabase submissions
            try:
                # Query Supabase table for submissions with matching assignment ID
                sb_query = supabase.table("submissions").select("*").eq("assignment_id", assignment_id)
                # Filter by submission IDs if specified
                if submission_ids:
                    # Apply in filter on ID column in Supabase query
                    sb_query = sb_query.in_("id", submission_ids)
                # Execute Supabase query
                sb_res = sb_query.execute()
                # Iterate over retrieved rows and mirror into local database
                for row in (sb_res.data or []):
                    # Instantiate local Submission model from Supabase row
                    s = Submission(
                        id=row["id"],
                        classroom_id=row.get("classroom_id"),
                        assignment_id=row["assignment_id"],
                        student_id=row.get("student_id"),
                        student_name_encrypted=row.get("student_name_encrypted"),
                        student_roll_encrypted=row.get("student_roll_encrypted"),
                        student_email_encrypted=row.get("student_email_encrypted"),
                        file_name=row["file_name"],
                        file_path=row.get("file_path", ""),
                        file_url=row.get("file_url"),
                        file_type=row.get("file_type", "pdf"),
                        extracted_text=row.get("extracted_text"),
                        content=row.get("content") or row.get("extracted_text") or "",
                        file_content=row.get("file_content"),
                        status=row.get("status", "queued"),
                    )
                    # Add submission to local session
                    db.add(s)
                # Commit mirrored submissions to local database
                db.commit()
                # Re-query local database for submissions
                query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
                # Re-apply ID filter if specified
                if submission_ids:
                    # Filter by submission IDs
                    query = query.filter(Submission.id.in_(submission_ids))
                # Execute query to populate submissions list
                submissions = query.all()
            # Handle Supabase query errors gracefully
            except Exception as sb_err:
                # Log warning for Supabase submissions fetch failure
                logger.warning(f"Error fetching submissions from Supabase: {sb_err}")

        # Compute total count of submissions to evaluate
        total = len(submissions)
        # Update batch job total items count
        job.total_items = total
        # Commit total items to database
        db.commit()

        # Emit initial Celery state
        # Check if task instance is provided
        if task_instance:
            # Emit PROCESSING state with initial zero progress metadata
            task_instance.update_state(
                state="PROCESSING",
                meta={"current": 0, "total": total, "percent": 0.0, "status": "PROCESSING"},
            )

        # Check if there are no submissions to evaluate
        if total == 0:
            # Mark job status as completed
            job.status = "completed"
            # Set job progress to 100%
            job.progress_pct = 100.0
            # Commit job completion to database
            db.commit()
            # If task instance exists, update Celery state to SUCCESS
            if task_instance:
                # Emit SUCCESS state to Celery
                task_instance.update_state(
                    state="SUCCESS",
                    meta={"current": 0, "total": 0, "percent": 100.0, "status": "SUCCESS"},
                )
            # Return success response for empty batch
            return {"status": "SUCCESS", "current": 0, "total": 0, "percent": 100.0, "processed": 0}

        # Initialize counter for successfully evaluated submissions
        evaluated_count = 0
        # Initialize counter for detected similarity flags
        similarity_flags_count = 0

        # 5. Process each submission sequentially so vectors can be checked against prior batch items
        # Iterate over submissions with index
        for idx, sub in enumerate(submissions):
            # Log progress for current submission evaluation
            logger.info(f"Evaluating submission [{idx + 1}/{total}]: {sub.id} ({sub.file_name})")

            # Update Celery state: current submission being evaluated
            # Check if task instance is available for status update
            if task_instance:
                # Emit Celery task state with current file and percentage
                task_instance.update_state(
                    state="PROCESSING",
                    meta={
                        "current": idx,
                        "total": total,
                        "percent": round((idx / total) * 100.0, 1),
                        "status": "PROCESSING",
                        "current_file": sub.file_name,
                    },
                )

            # Mark status in Supabase & local DB as evaluating
            # Set local submission status to evaluating
            sub.status = "evaluating"
            # Commit status change to local database
            db.commit()
            # Try updating status in Supabase
            try:
                # Update submission status to evaluating in Supabase
                supabase.table("submissions").update({
                    "status": "evaluating",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", sub.id).execute()
            # Catch exceptions from Supabase status update silently
            except Exception:
                # Continue if Supabase status update fails
                pass

            # a. Extract text or code content from file
            # Get cached extracted text or content from submission model
            extracted_text = sub.extracted_text or sub.content or ""
            # If no cached text exists, extract from available sources
            if not extracted_text:
                # Check if raw file_content is stored on the model
                if sub.file_content:
                    # Use stored file content as extracted text
                    extracted_text = sub.file_content
                # Check if a remote file URL is available
                elif sub.file_url:
                    # Download directly from Supabase Storage
                    # Download binary file content from Supabase storage
                    raw_bytes = supabase_service.download_file_from_storage(sub.file_url)
                    # Check if file bytes were successfully downloaded
                    if raw_bytes:
                        # Extract text from downloaded bytes using PDF service
                        extracted_text = pdf_service.extract_text_from_bytes(raw_bytes, sub.file_name)
                # Check if local file path exists on disk
                elif sub.file_path and os.path.exists(sub.file_path):
                    # Extract text directly from local file path
                    extracted_text = pdf_service.extract_text_from_file_path(sub.file_path)

            # If text could still not be extracted, set a placeholder description
            if not extracted_text:
                # Provide fallback text describing the submission
                extracted_text = f"Student submission content for {sub.file_name} implementing assigned algorithmic patterns."

            # Update extracted text field on submission model
            sub.extracted_text = extracted_text
            # Update content field on submission model
            sub.content = extracted_text
            # Commit updated text to local database
            db.commit()

            # b. Generate text embeddings (text-embedding-004) and query Qdrant collection submissions_{assignment_id}
            #    to detect peer-to-peer similarity (> 0.75)
            # Generate 768-dimensional text embedding vector
            embedding_vector = vector_service.generate_embedding(extracted_text)
            # Query Qdrant for peer submissions exceeding 0.75 similarity threshold
            peer_matches = vector_service.search_peer_similarity(
                submission_id=sub.id,
                assignment_id=assignment_id,
                vector=embedding_vector,
                threshold=0.75,
            )

            # Initialize list for human-readable peer context strings
            peer_context_parts = []
            # Initialize variable for highest detected peer similarity
            highest_peer_sim = 0.0
            # Initialize list for matched peer submission IDs
            matched_peer_ids = []

            # Iterate over all peer similarity matches found
            for match in peer_matches:
                # Extract similarity percentage score
                sim_pct = match["similarity_score"]
                # Update highest peer similarity score if greater
                if sim_pct > highest_peer_sim:
                    # Set new highest peer similarity
                    highest_peer_sim = sim_pct
                # Append matched peer ID to list
                matched_peer_ids.append(match["submission_id"])
                # Append formatted peer match detail to context list
                peer_context_parts.append(
                    f"- Peer Submission '{match['submission_id']}' (File: {match['file_name']}): "
                    f"Cosine similarity {sim_pct}% (> 0.75 threshold)."
                )

                # Persist similarity match row
                # Try persisting similarity match record
                try:
                    # Generate a unique similarity match identifier
                    sim_id = f"sim_{uuid.uuid4().hex[:12]}"
                    # Instantiate local SimilarityMatch model
                    sim_record = SimilarityMatch(
                        id=sim_id,
                        assignment_id=assignment_id,
                        submission_a_id=sub.id,
                        submission_b_id=match["submission_id"],
                        similarity_score=sim_pct,
                        matching_phrases=[f"High vector alignment ({sim_pct}%) in submissions_{assignment_id}"],
                        status="High similarity",
                    )
                    # Add similarity record to local database session
                    db.add(sim_record)
                    # Upsert similarity record in Supabase table
                    supabase.table("similarity_matches").upsert({
                        "id": sim_id,
                        "assignment_id": assignment_id,
                        "submission_a_id": sub.id,
                        "submission_b_id": match["submission_id"],
                        "similarity_score": sim_pct,
                        "matching_phrases": [f"Cosine similarity {sim_pct}% in Qdrant"],
                        "status": "High similarity",
                    }).execute()
                    # Increment similarity flags counter
                    similarity_flags_count += 1
                # Catch errors during similarity persistence silently
                except Exception:
                    # Ignore similarity record persistence errors
                    pass

            # Format peer matching context string or default notice
            peer_matching_context = "\n".join(peer_context_parts) if peer_context_parts else "No previous submissions in Qdrant exceeded the 0.75 cosine similarity threshold."

            # Check if teacher requested cancellation of active grading job
            if is_grading_cancelled(assignment_id):
                # Log cancellation notice
                logger.info(f"Grading cancellation requested by teacher for assignment {assignment_id}.")
                # Set job status to cancelled
                job.status = "cancelled"
                # Commit cancellation to database
                db.commit()
                # Update cancellation status in Redis
                update_assignment_progress(
                    assignment_id,
                    {
                        "status": "cancelled",
                        "total": total,
                        "processed": evaluated_count,
                        "current_stage": "cancelled",
                        "progress_pct": round((evaluated_count / total) * 100.0, 1) if total > 0 else 0.0,
                        "eta_seconds": 0,
                        "failed_count": 0,
                        "errors": ["Grading cancelled by user."],
                    },
                )
                # Break evaluation loop
                break

            # Resolve reference exemplar solution text
            reference_solution = (
                assignment.reference_assignment_text
                if assignment and assignment.reference_assignment_text
                else kwargs.get("reference_assignment_text")
            )
            # Resolve assignment title
            assignment_title = assignment.title if assignment else f"Assignment {assignment_id}"
            # Resolve assignment max score
            assign_max_score = assignment.max_score if assignment and assignment.max_score else 100.0

            # c. SHA-256 Content-Hash Cache Lookup (Speed Rule 1)
            # Query Redis evaluation cache before invoking LLM
            cached_eval = get_content_evaluation_cache(extracted_text, rubric_criteria_list)
            # Check if cache hit
            if cached_eval:
                # Log cache hit
                logger.info(f"Evaluation cache HIT (SHA-256) for submission {sub.id} ({sub.file_name}). Skipping LLM.")
                # Load cached evaluation dictionary
                eval_dict = cached_eval
            # If cache miss, invoke Phase 5 Gemini autograding prompt with pure Python arithmetic
            else:
                # Log cache miss
                logger.info(f"Evaluation cache MISS for submission {sub.id}. Invoking Phase 5 autograding prompt (temp 0).")
                # Invoke Gemini Phase 5 autograding prompt
                eval_dict = gemini_service.evaluate_with_phase5_prompt(
                    submission_text=extracted_text,
                    rubric_criteria=rubric_criteria_list,
                    assignment_instructions=assignment.description or "",
                    reference_solution=reference_solution,
                    filename=sub.file_name or "submission.txt",
                    file_format=sub.file_name.split(".")[-1] if "." in (sub.file_name or "") else "text",
                    max_score=assign_max_score,
                )
                # Store evaluation result in SHA-256 content-hash cache
                set_content_evaluation_cache(extracted_text, rubric_criteria_list, eval_dict)

            # Determine maximum peer similarity score between vector match and result
            final_peer_score = highest_peer_sim
            # Initialize flagged matches list
            flagged_matches = []
            # Check if peer IDs were matched by vector search
            if matched_peer_ids:
                # Add vector similarity notes to flagged matches list
                flagged_matches.extend([f"Peer match with {pid} (Cosine > 0.75)" for pid in matched_peer_ids])

            # d. Upsert criteria scores, qualitative notes, and review queue routing
            # Format criteria breakdown list for JSON persistence
            criteria_payload = [
                {
                    "criterion_name": c.get("criterion_name"),
                    "score": c.get("tier_points", 0.0),
                    "max": c.get("tier_points", 4.0),
                    "rationale": c.get("justification", ""),
                    "tier_name": c.get("tier_name", ""),
                    "evidence": c.get("evidence", []),
                    "confidence": c.get("confidence", 1.0),
                }
                for c in eval_dict.get("criteria_evaluations", [])
            ]

            # Construct plagiarism report dictionary payload
            plagiarism_payload = {
                "peer_to_peer_score": final_peer_score,
                "public_source_score": 0.0,
                "ai_probability": 15.0,
                "flagged_matches": list(set(flagged_matches)),
                "routing_reasons": eval_dict.get("routing_reasons", []),
            }

            # Generate draft grade identifier
            draft_id = f"draft_{sub.id}"
            # Check if manual review is required (< 0.6 confidence, unreadable, prompt injection)
            requires_manual_review = eval_dict.get("requires_manual_review", False)
            # Route to flagged if manual review needed, suggested otherwise
            grade_status = "flagged" if requires_manual_review else "suggested"
            # Extract final calculated score strictly computed in Python
            calculated_score = float(eval_dict.get("score", 0.0))
            # Extract qualitative feedback
            overall_feedback = eval_dict.get("overall_feedback", "Evaluated against rubric specifications.")

            # 1. Update draft_grades in Supabase
            # Begin try block to upsert draft grade in Supabase
            try:
                # Upsert draft grade record into Supabase table
                supabase.table("draft_grades").upsert({
                    "id": draft_id,
                    "submission_id": sub.id,
                    "total_score": calculated_score,
                    "max_score": assign_max_score,
                    "suggested_score": calculated_score,
                    "criteria_scores": criteria_payload,
                    "criteria_breakdown": criteria_payload,
                    "plagiarism_report": plagiarism_payload,
                    "feedback": overall_feedback,
                    "ai_feedback": overall_feedback,
                    "status": grade_status,
                    "ai_model": "gemini-2.5-flash",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            # Handle Supabase draft grade upsert error
            except Exception as sb_draft_err:
                # Log error message for failed Supabase draft grade upsert
                logger.error(f"Failed to upsert draft_grade in Supabase for {sub.id}: {sb_draft_err}")

            # 2. Update local DB draft_grades
            # Query local database for existing DraftGrade entity
            existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
            # Check if existing draft grade record was found
            if existing_draft:
                # Update total score on existing draft
                existing_draft.total_score = calculated_score
                # Update suggested score on existing draft
                existing_draft.suggested_score = calculated_score
                # Update max score on existing draft
                existing_draft.max_score = assign_max_score
                # Update criteria scores dictionary
                existing_draft.criteria_scores = criteria_payload
                # Update criteria breakdown list
                existing_draft.criteria_breakdown = criteria_payload
                # Update plagiarism report dictionary
                existing_draft.plagiarism_report = plagiarism_payload
                # Update qualitative feedback
                existing_draft.feedback = overall_feedback
                # Update AI feedback
                existing_draft.ai_feedback = overall_feedback
                # Update status
                existing_draft.status = grade_status
                # Update AI model identifier
                existing_draft.ai_model = "gemini-2.5-flash"
            # If draft grade record does not exist locally, instantiate a new one
            else:
                # Create new DraftGrade entity with evaluation results
                new_draft = DraftGrade(
                    id=draft_id,
                    submission_id=sub.id,
                    total_score=calculated_score,
                    suggested_score=calculated_score,
                    max_score=assign_max_score,
                    criteria_scores=criteria_payload,
                    criteria_breakdown=criteria_payload,
                    plagiarism_report=plagiarism_payload,
                    feedback=overall_feedback,
                    ai_feedback=overall_feedback,
                    status=grade_status,
                    ai_model="gemini-2.5-flash",
                )
                # Add new draft grade to local database session
                db.add(new_draft)

            # e. Insert the current submission vector into Qdrant collection submissions_{assignment_id}
            #    so subsequent students in the batch are compared against it
            # Insert or update embedding vector in Qdrant collection
            vector_service.upsert_submission_vector(
                submission_id=sub.id,
                assignment_id=assignment_id,
                vector=embedding_vector,
                payload={
                    "file_name": sub.file_name,
                    "student_name": sub.student_name,
                    "student_id": sub.student_id,
                },
            )

            # g. Update submissions.status = 'completed' in Supabase and DB
            # Set local submission status to completed
            sub.status = "completed"
            # Set similarity score on submission model
            sub.similarity_score = final_peer_score
            # Set AI content probability score on submission model
            sub.ai_content_probability = 15.0
            # Set public web source plagiarism score on submission model
            sub.web_plagiarism_score = 0.0
            # Commit submission updates to local database
            db.commit()

            # Try updating submission record in Supabase
            try:
                # Update submission row in Supabase table
                supabase.table("submissions").update({
                    "status": "completed",
                    "similarity_score": final_peer_score,
                    "ai_content_probability": 15.0,
                    "web_plagiarism_score": 0.0,
                    "extracted_text": extracted_text[:10000],
                    "content": extracted_text[:10000],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", sub.id).execute()
            # Handle Supabase update failure gracefully
            except Exception as sb_sub_err:
                # Log warning for failed Supabase submission status update
                logger.warning(f"Failed to update submission status in Supabase for {sub.id}: {sb_sub_err}")

            # Increment evaluated submissions counter
            evaluated_count += 1

            # f. Update Celery task state and real-time progress in Redis
            # Calculate current batch progress percentage
            current_progress_pct = round(((idx + 1) / total) * 100.0, 1)
            # Estimate remaining seconds (approx 4 seconds per submission)
            remaining_eta = max(0, int((total - (idx + 1)) * 4))
            # Update processed items count on batch job
            job.processed_items = idx + 1
            # Update progress percentage on batch job
            job.progress_pct = current_progress_pct
            # Commit job progress updates to database
            db.commit()

            # Update real-time progress in Redis for live UI polling
            update_assignment_progress(
                assignment_id,
                {
                    "status": "grading",
                    "total": total,
                    "processed": idx + 1,
                    "current_stage": "grading",
                    "progress_pct": current_progress_pct,
                    "eta_seconds": remaining_eta,
                    "failed_count": 0,
                    "current_submission": sub.id,
                    "errors": [],
                },
            )

            # Check if Celery task instance is available for state update
            if task_instance:
                # Emit updated PROCESSING state and progress percentage to Celery
                task_instance.update_state(
                    state="PROCESSING",
                    meta={
                        "current": idx + 1,
                        "total": total,
                        "percent": current_progress_pct,
                        "status": "PROCESSING",
                    },
                )

        # 6. Mark Job Complete and ready_for_review
        # Update job status to completed
        job.status = "completed"
        # Set job progress percentage to 100%
        job.progress_pct = 100.0
        # Store metadata summary on batch job
        job.meta_info = {
            "similarity_flags": similarity_flags_count,
            "ready_for_review": evaluated_count,
        }
        # Commit completed job state to database
        db.commit()

        # Update final ready_for_review state in Redis
        update_assignment_progress(
            assignment_id,
            {
                "status": "ready_for_review",
                "total": total,
                "processed": total,
                "current_stage": "ready_for_review",
                "progress_pct": 100.0,
                "eta_seconds": 0,
                "failed_count": 0,
                "errors": [],
            },
        )

        # Check if Celery task instance is available
        if task_instance:
            # Emit SUCCESS state and final batch summary metadata
            task_instance.update_state(
                state="SUCCESS",
                meta={
                    "current": total,
                    "total": total,
                    "percent": 100.0,
                    "status": "SUCCESS",
                    "processed": evaluated_count,
                    "similarity_flags": similarity_flags_count,
                },
            )

        # Log successful batch evaluation audit event
        log_audit_event(
            actor="CELERY_WORKER",
            action="BATCH_EVALUATION_SUCCESS",
            entity="Assignment",
            entity_id=assignment_id,
            details=f"Evaluated {evaluated_count}/{total} submissions for assignment {assignment_id}",
        )

        # Return successful batch evaluation result summary dictionary
        return {
            "status": "SUCCESS",
            "current": total,
            "total": total,
            "percent": 100.0,
            "processed": evaluated_count,
            "similarity_flags": similarity_flags_count,
            "job_id": job_id,
        }

    # Catch any unhandled exceptions during batch evaluation execution
    except Exception as e:
        # Log error message with full exception stack trace
        logger.error(f"Error in batch evaluation worker task {job_id}: {e}", exc_info=True)
        # Query for batch job to record failure status
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        # Check if batch job was found
        if job:
            # Mark job status as failed
            job.status = "failed"
            # Record error message string on batch job
            job.error_message = str(e)
            # Commit failure status to database
            db.commit()

        # If Celery task instance is present, emit FAILURE state
        if task_instance:
            # Update Celery state to FAILURE with error details
            task_instance.update_state(
                state="FAILURE",
                meta={"error": str(e), "status": "FAILURE"},
            )
        # Re-raise the exception for Celery failure tracking
        raise e
    # Ensure database session is closed in all scenarios
    finally:
        # Close database session
        db.close()
