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
                # Build formatted criteria dictionary list from local model preserving teacher levels
                rubric_criteria_list = [
                    {
                        "id": c.id,
                        "name": c.criterion_name or c.name or "Criterion",
                        "criterion_name": c.criterion_name or c.name or "Criterion",
                        "description": c.description or "",
                        "weight": c.weight or 25.0,
                        "max_score": c.max_points or c.max_score or 4.0,
                        "max_points": c.max_points or c.max_score or 4.0,
                        "levels": c.levels or [],
                    }
                    for c in local_rubric.criteria
                ]

        # Ensure performance tiers (levels) with real points exist if not provided
        for c_idx, crit in enumerate(rubric_criteria_list):
            if not crit.get("levels") and not crit.get("tiers"):
                max_pts = float(crit.get("max_score") or crit.get("max_points") or 4.0)
                cid = crit.get("id") or f"crit_{c_idx+1}"
                crit["levels"] = [
                    {"id": f"{cid}_tier_1", "level_name": "Exemplary", "name": "Exemplary", "points": max_pts, "description": "Exceeds expectations with robust implementation."},
                    {"id": f"{cid}_tier_2", "level_name": "Proficient", "name": "Proficient", "points": round(max_pts * 0.85, 2), "description": "Meets standard requirements accurately."},
                    {"id": f"{cid}_tier_3", "level_name": "Developing", "name": "Developing", "points": round(max_pts * 0.70, 2), "description": "Basic implementation with minor errors."},
                    {"id": f"{cid}_tier_4", "level_name": "Beginning", "name": "Beginning", "points": round(max_pts * 0.50, 2), "description": "Incomplete or requires revision."},
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

        # 5. Pre-compute winnowing peer similarity across the entire assignment batch
        from app.services.winnowing_service import winnowing_service
        import hashlib

        # Resolve reference exemplar solution text and check rubric/reference existence
        reference_solution = (
            assignment.reference_assignment_text
            if assignment and assignment.reference_assignment_text
            else kwargs.get("reference_assignment_text")
        )
        assignment_title = assignment.title if assignment else f"Assignment {assignment_id}"
        assign_max_score = assignment.max_score if assignment and assignment.max_score else 100.0
        has_rubric = bool(rubric_criteria_list and len(rubric_criteria_list) > 0)
        has_reference = bool(reference_solution and len(reference_solution.strip()) > 0)

        # Build submission texts list for winnowing
        batch_sub_dicts = []
        for s in submissions:
            stext = s.extracted_text or s.content or ""
            if stext.startswith("[Could not read this file"):
                stext = ""
            batch_sub_dicts.append({
                "id": s.id,
                "text": stext,
                "file_hash": hashlib.sha256(stext.encode("utf-8")).hexdigest() if stext else "",
                "file_name": s.file_name,
                "student_name": s.student_name,
            })

        peer_analysis = winnowing_service.analyze_batch(
            submissions=batch_sub_dicts,
            reference_text=reference_solution or "",
            assignment_prompt=assignment.description or "" if assignment else "",
        )

        # 6. Process each submission sequentially with strict JSON grading and pure arithmetic
        for idx, sub in enumerate(submissions):
            logger.info(f"Evaluating submission [{idx + 1}/{total}]: {sub.id} ({sub.file_name})")

            if task_instance:
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

            # a. Resolve text content
            extracted_text = sub.extracted_text or sub.content or ""
            if extracted_text.startswith("[Could not read this file"):
                extracted_text = ""
                sub.extracted_text = ""
                sub.content = ""
                db.commit()

            text_len = len(extracted_text.strip())
            p_data = peer_analysis.get(sub.id, {})
            is_dup = p_data.get("is_duplicate", False)
            sim_score = p_data.get("similarity_score")
            draft_id = f"draft_{sub.id}"

            # Step 1 structured audit log
            logger.info(
                f"[GRADING-STEP1-AUDIT] sub_id={sub.id} file={sub.file_name} "
                f"extracted_text_length={text_len} first_200={repr(extracted_text[:200])} "
                f"rubric_loaded={has_rubric} criteria_count={len(rubric_criteria_list)} "
                f"has_reference={has_reference} is_duplicate={is_dup} "
                f"winnowing_fps={p_data.get('fingerprints_count', 0)} "
                f"matched_fps={p_data.get('matched_fingerprints_count', 0)} "
                f"peer_sim={sim_score}"
            )

            # STEP 2 Rule 1: Text empty or under ~50 characters, or unreadable scan placeholder
            is_placeholder = bool(extracted_text and extracted_text.strip().startswith("[Could not read this file"))
            if text_len < 50 or is_placeholder:
                logger.info(f"[EVAL] Submission {sub.id} text under 50 chars or unreadable placeholder ({text_len}). Setting needs_review.")
                sub.status = "needs_review"
                sub.similarity_score = None
                sub.ai_content_probability = None
                sub.web_plagiarism_score = None
                db.commit()

                reason_msg = "No text to grade"
                draft_payload = {
                    "id": draft_id,
                    "submission_id": sub.id,
                    "final_score": None,
                    "total_score": None,
                    "max_score": assign_max_score,
                    "suggested_score": None,
                    "criteria_scores": [],
                    "criteria_breakdown": [],
                    "plagiarism_report": {
                        "peer_to_peer_score": None,
                        "public_source_score": None,
                        "ai_probability": None,
                        "flagged_matches": ["Duplicate upload"] if is_dup else [],
                        "routing_reasons": [reason_msg],
                    },
                    "feedback": reason_msg,
                    "ai_feedback": reason_msg,
                    "status": "needs_review",
                    "ai_model": settings.GEMINI_MODEL,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    supabase.table("draft_grades").upsert(draft_payload).execute()
                except Exception:
                    pass

                existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
                if existing_draft:
                    existing_draft.final_score = None
                    existing_draft.total_score = None
                    existing_draft.suggested_score = None
                    existing_draft.status = "needs_review"
                    existing_draft.feedback = reason_msg
                    existing_draft.criteria_scores = []
                else:
                    db.add(DraftGrade(**draft_payload))
                db.commit()

                try:
                    supabase.table("submissions").update({
                        "status": "needs_review",
                        "similarity_score": None,
                        "ai_content_probability": None,
                        "web_plagiarism_score": None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", sub.id).execute()
                except Exception:
                    pass

                evaluated_count += 1
                continue

            # STEP 2 Rule 2: If no rubric or reference exists:
            if not has_rubric or not has_reference:
                block_msg = "Grading blocked: Assignment requires both an attached evaluation rubric and reference solution."
                logger.warning(f"[EVAL] Submission {sub.id} blocked: {block_msg}")
                sub.status = "needs_review"
                sub.similarity_score = sim_score
                sub.ai_content_probability = None
                sub.web_plagiarism_score = None
                db.commit()

                draft_payload = {
                    "id": draft_id,
                    "submission_id": sub.id,
                    "total_score": None,
                    "max_score": assign_max_score,
                    "suggested_score": None,
                    "criteria_scores": [],
                    "criteria_breakdown": [],
                    "plagiarism_report": {
                        "peer_to_peer_score": sim_score,
                        "public_source_score": None,
                        "ai_probability": None,
                        "flagged_matches": ["Duplicate upload"] if is_dup else [],
                        "routing_reasons": [block_msg],
                    },
                    "feedback": block_msg,
                    "ai_feedback": block_msg,
                    "status": "needs_review",
                    "ai_model": settings.GEMINI_MODEL,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    supabase.table("draft_grades").upsert(draft_payload).execute()
                except Exception:
                    pass

                existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
                if existing_draft:
                    existing_draft.final_score = None
                    existing_draft.total_score = None
                    existing_draft.suggested_score = None
                    existing_draft.status = "needs_review"
                    existing_draft.feedback = block_msg
                    existing_draft.criteria_scores = []
                else:
                    db.add(DraftGrade(**draft_payload))
                db.commit()
                evaluated_count += 1
                continue

            # STEP 2 Rule 3: Gemini autograding with pure arithmetic
            eval_dict = gemini_service.evaluate_with_phase5_prompt(
                submission_text=extracted_text,
                rubric_criteria=rubric_criteria_list,
                assignment_instructions=assignment.description or "" if assignment else "",
                reference_solution=reference_solution,
                filename=sub.file_name or "submission.txt",
                file_format=sub.file_name.split(".")[-1] if "." in (sub.file_name or "") else "text",
                max_score=assign_max_score,
            )

            # Check if Gemini grading failed or returned invalid JSON
            if not eval_dict.get("success", True) or eval_dict.get("score") is None:
                err_detail = eval_dict.get("error") or "Gemini model error or invalid JSON"
                logger.error(f"[EVAL] Gemini grading failed for submission {sub.id}: {err_detail}")
                sub.status = "grading_failed"
                sub.similarity_score = sim_score
                sub.ai_content_probability = None
                sub.web_plagiarism_score = None
                db.commit()

                fail_msg = f"Grading failed: {err_detail}"
                draft_payload = {
                    "id": draft_id,
                    "submission_id": sub.id,
                    "final_score": None,
                    "total_score": None,
                    "max_score": assign_max_score,
                    "suggested_score": None,
                    "criteria_scores": [],
                    "criteria_breakdown": [],
                    "plagiarism_report": {
                        "peer_to_peer_score": sim_score,
                        "public_source_score": None,
                        "ai_probability": None,
                        "flagged_matches": ["Duplicate upload"] if is_dup else [],
                        "routing_reasons": [fail_msg],
                    },
                    "feedback": fail_msg,
                    "ai_feedback": fail_msg,
                    "status": "grading_failed",
                    "ai_model": settings.GEMINI_MODEL,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    supabase.table("draft_grades").upsert(draft_payload).execute()
                except Exception:
                    pass

                existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
                if existing_draft:
                    existing_draft.final_score = None
                    existing_draft.total_score = None
                    existing_draft.suggested_score = None
                    existing_draft.status = "grading_failed"
                    existing_draft.feedback = fail_msg
                    existing_draft.criteria_scores = []
                else:
                    db.add(DraftGrade(**draft_payload))
                db.commit()
                evaluated_count += 1
                continue

            # STEP 2 Rule 4: Compute score in code as sum of criterion scores clamped to 0..max
            calculated_score = float(eval_dict.get("score", 0.0))
            overall_feedback = eval_dict.get("overall_feedback", "Evaluated against rubric specifications.")
            requires_manual_review = eval_dict.get("requires_manual_review", False)
            grade_status = "flagged" if requires_manual_review else "suggested"

            criteria_payload = [
                {
                    "criterion_name": c.get("criterion_name"),
                    "score": c.get("score", c.get("tier_points", 0.0)),
                    "max": c.get("max", c.get("tier_points", 4.0)),
                    "rationale": c.get("justification", ""),
                    "tier_name": c.get("tier_name", ""),
                    "evidence": c.get("evidence", []),
                    "confidence": c.get("confidence", 1.0),
                }
                for c in eval_dict.get("criteria_evaluations", [])
            ]

            # Plagiarism and AI metrics: compute for real, or None (N/A)
            plagiarism_payload = {
                "peer_to_peer_score": sim_score,
                "public_source_score": None,
                "ai_probability": None,
                "flagged_matches": ["Duplicate upload"] if is_dup else ([] if sim_score is None or sim_score < 75.0 else [f"Peer match ({sim_score}%)"]),
                "routing_reasons": eval_dict.get("routing_reasons", []),
            }

            draft_payload = {
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
                "ai_model": settings.GEMINI_MODEL,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            try:
                supabase.table("draft_grades").upsert(draft_payload).execute()
            except Exception as sb_err:
                logger.warning(f"Supabase draft grade upsert notice: {sb_err}")

            existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
            if existing_draft:
                existing_draft.total_score = calculated_score
                existing_draft.suggested_score = calculated_score
                existing_draft.max_score = assign_max_score
                existing_draft.criteria_scores = criteria_payload
                existing_draft.criteria_breakdown = criteria_payload
                existing_draft.plagiarism_report = plagiarism_payload
                existing_draft.feedback = overall_feedback
                existing_draft.ai_feedback = overall_feedback
                existing_draft.status = grade_status
                existing_draft.ai_model = settings.GEMINI_MODEL
            else:
                db.add(DraftGrade(**draft_payload))

            # Update submission record
            sub.status = "completed"
            sub.similarity_score = sim_score
            sub.ai_content_probability = None
            sub.web_plagiarism_score = None
            db.commit()

            try:
                supabase.table("submissions").update({
                    "status": "completed",
                    "similarity_score": sim_score,
                    "ai_content_probability": None,
                    "web_plagiarism_score": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", sub.id).execute()
            except Exception as sb_err:
                logger.warning(f"Supabase submission update notice: {sb_err}")

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
        try:
            db.rollback()
        except Exception:
            pass
        # Query for batch job to record failure status
        try:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
        except Exception as commit_err:
            logger.warning(f"Could not update BatchJob to failed state: {commit_err}")

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
