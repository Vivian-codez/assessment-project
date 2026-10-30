# Module docstring describing the local-first SQLAlchemy-backed database service layer and fallback behavior
"""Database Service Layer – local-first, SQLAlchemy-backed.

When USE_SUPABASE=false (default) every method writes/reads directly via the
SQLAlchemy ORM (local PostgreSQL or SQLite).

When USE_SUPABASE=true the Supabase PostgREST client is attempted first, with
an automatic SQLAlchemy fallback on any error (unchanged behaviour).

Storage: Supabase Storage is replaced by local filesystem storage under
settings.UPLOADS_DIR.  Files are served via the FastAPI static-files mount or
directly from disk.
"""

# Import operating system module for path resolution and directory management
import os
# Import uuid module for generating random unique identifiers
import uuid
# Import mimetypes module to guess file content-type from file extensions
import mimetypes
# Import datetime and timezone classes for UTC timestamp creation
from datetime import datetime, timezone
# Import typing utilities for generic types, dictionaries, lists, and optional values
from typing import Any, Dict, List, Optional

# Import global application configuration settings
from app.core.config import settings
# Import structured system logger
from app.core.logging import logger
# Import FERPA encryption cipher for PII protection
from app.core.security import ferpa_cipher
# Import SQLAlchemy session factory for database connection acquisition
from app.core.database import SessionLocal
# Import Course database model
from app.models.course import Course
# Import Instructor database model
from app.models.instructor import Instructor
# Import Submission database model
from app.models.submission import Submission
# Import Rubric and RubricCriterion database models
from app.models.rubric import Rubric, RubricCriterion
# Import DraftGrade database model
from app.models.draft_grade import DraftGrade
# Import AuditLog database model
from app.models.audit_log import AuditLog
# Import SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch

# Import optional Supabase client (no-op stub when USE_SUPABASE=false)
from app.core.supabase import supabase as _sb

# Resolve absolute path for uploads directory using environment variable or config setting
_UPLOADS_DIR: str = os.path.abspath(
    os.environ.get("UPLOADS_DIR", settings.UPLOADS_DIR)
)
# Ensure the uploads directory exists on the filesystem
os.makedirs(_UPLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Helper function converting an ORM Submission model instance to a JSON-compatible dictionary
def _sub_to_dict(s: Submission) -> Dict[str, Any]:
    # Construct dictionary containing submission attributes with decrypted PII and formatted dates
    return {
        # Unique submission identifier
        "id": s.id,
        # Assignment identifier
        "assignment_id": s.assignment_id,
        # Decrypted student full name
        "student_name": s.student_name,
        # Decrypted student roll number
        "student_roll": s.student_roll,
        # Decrypted student email address
        "student_email": s.student_email,
        # Original uploaded file name
        "file_name": s.file_name,
        # Local disk file path
        "file_path": s.file_path,
        # Public or static URL to the uploaded file
        "file_url": s.file_url,
        # Extracted plain text content
        "extracted_text": s.extracted_text,
        # Raw file content text
        "file_content": s.file_content,
        # Primary document content
        "content": s.content,
        # Plagiarism similarity percentage score
        "similarity_score": s.similarity_score,
        # AI-generated content probability percentage
        "ai_content_probability": s.ai_content_probability,
        # Public web plagiarism score or fallback default to 0.0
        "web_plagiarism_score": getattr(s, "web_plagiarism_score", 0.0),
        # Matched web sources list or fallback to empty list
        "web_sources": getattr(s, "web_sources", []),
        # Workflow status of the submission
        "status": s.status,
        # ISO-formatted creation timestamp string or None
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# Class providing unified data operations backed primarily by SQLAlchemy with optional Supabase fallback
class SupabaseService:
    # Class docstring explaining dual architecture
    """Unified data service – SQLAlchemy primary, optional Supabase secondary."""

    # Initializer capturing client reference
    def __init__(self):
        # Store database client reference
        self.client = _sb

    # =========================================================================
    # Courses
    # =========================================================================

    # Method to query courses matching an optional search term
    def get_courses(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        # Method docstring describing course fetching logic
        """Fetch courses from local DB (with optional Supabase PostgREST fallback)."""
        # If cloud Supabase integration is explicitly enabled in config
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Prepare PostgREST query on courses table
                query = self.client.table("courses").select("*")
                # Add case-insensitive name filter if search string provided
                if search:
                    # Filter names matching pattern
                    query = query.ilike("name", f"%{search}%")
                # Execute PostgREST query
                res = query.execute()
                # If records returned, return data list directly
                if res.data:
                    # Return list of course dictionaries
                    return res.data
            # Catch PostgREST exceptions and fallback to local DB
            except Exception as exc:
                # Log debug message with exception details
                logger.debug(f"Supabase courses query: {exc}")

        # Open local database session
        db = SessionLocal()
        # Ensure session is cleanly closed after query completes
        try:
            # Create base query for Course records
            q = db.query(Course)
            # Apply search filter if query text provided
            if search:
                # Construct wild-card SQL ILIKE pattern
                pattern = f"%{search}%"
                # Filter courses by name or code containing pattern
                q = q.filter(Course.name.ilike(pattern) | Course.code.ilike(pattern))
            # Return list of mapped course dictionaries
            return [
                # Dictionary mapping for each course record
                {
                    # Course unique identifier
                    "id": c.id,
                    # Course display name
                    "name": c.name,
                    # Course code string
                    "code": c.code,
                    # Section cohort identifier
                    "section": c.section,
                    # UI color tone string
                    "tone": c.tone,
                    # Count of enrolled students
                    "students_count": c.students_count,
                    # Linked instructor identifier
                    "instructor_id": c.instructor_id,
                    # ISO-formatted creation timestamp string or None
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                # Iterate through all matching Course records
                for c in q.all()
            ]
        # Guarantee database session teardown
        finally:
            # Close session returning connection to pool
            db.close()

    # Method to retrieve a single course by its unique identifier
    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap PostgREST call in try-except block
            try:
                # Query courses table for matching record ID
                res = self.client.table("courses").select("*").eq("id", course_id).execute()
                # Return first record if found
                if res.data:
                    # Return course dictionary
                    return res.data[0]
            # Catch and log cloud query errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase course by id: {exc}")

        # Open local database session
        db = SessionLocal()
        # Ensure session closure
        try:
            # Query Course table filtering by course_id primary key
            c = db.query(Course).filter(Course.id == course_id).first()
            # If course record found, construct and return dictionary
            if c:
                # Return course dictionary
                return {
                    # Course unique identifier
                    "id": c.id,
                    # Course title
                    "name": c.name,
                    # Course code
                    "code": c.code,
                    # Class section
                    "section": c.section,
                    # Card color tone
                    "tone": c.tone,
                    # Enrolled students count
                    "students_count": c.students_count,
                    # Linked instructor ID
                    "instructor_id": c.instructor_id,
                }
            # Return None if course does not exist
            return None
        # Guarantee session closure
        finally:
            # Close database session
            db.close()

    # =========================================================================
    # Instructors
    # =========================================================================

    # Method to retrieve instructor record by email address
    def get_instructor_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query instructors table by email address
                res = self.client.table("instructors").select("*").eq("email", email).execute()
                # If record found, return first result
                if res.data:
                    # Return instructor dictionary
                    return res.data[0]
            # Catch PostgREST error and fallback
            except Exception as exc:
                # Log debug message with exception details
                logger.debug(f"Supabase instructor by email: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Query Instructor table filtering by matching email address
            inst = db.query(Instructor).filter(Instructor.email == email).first()
            # If instructor found in local database, construct dictionary
            if inst:
                # Return mapped instructor dictionary
                return {
                    # Unique instructor identifier
                    "id": inst.id,
                    # Instructor display name
                    "name": inst.name,
                    # Email address
                    "email": inst.email,
                    # Title or functional role
                    "role": inst.role,
                    # Salted PBKDF2 password hash
                    "hashed_password": inst.hashed_password,
                    # Preferences dictionary or empty dict fallback
                    "preferences": inst.preferences or {},
                }
            # Return None if no instructor matched
            return None
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # =========================================================================
    # Submissions
    # =========================================================================

    # Method to fetch submissions for an assignment with optional status filter
    def get_submissions(
        self, assignment_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query submissions table filtered by assignment_id
                q = self.client.table("submissions").select("*").eq("assignment_id", assignment_id)
                # Apply optional status filter if provided
                if status:
                    # Filter by status string
                    q = q.eq("status", status)
                # Execute query
                res = q.execute()
                # Process records if returned
                if res.data:
                    # Initialize list of decrypted submission rows
                    rows = []
                    # Iterate through fetched rows
                    for row in res.data:
                        # Decrypt student name or fallback to 'Student'
                        row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Student"
                        # Decrypt student roll number or fallback to empty string
                        row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                        # Decrypt student email or fallback to empty string
                        row["student_email"] = ferpa_cipher.decrypt(row.get("student_email_encrypted", "")) or ""
                        # Append decrypted row to results list
                        rows.append(row)
                    # Return decrypted rows list
                    return rows
            # Catch PostgREST query errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase submissions: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Query Submission table filtered by assignment_id
            q = db.query(Submission).filter(Submission.assignment_id == assignment_id)
            # Apply status filter if provided
            if status:
                # Filter by status attribute
                q = q.filter(Submission.status == status)
            # Convert and return all matching submission models to dictionaries
            return [_sub_to_dict(s) for s in q.all()]
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # Method to retrieve a single submission by its unique identifier
    def get_submission_by_id(self, submission_id: str) -> Optional[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query submissions table by unique submission ID
                res = self.client.table("submissions").select("*").eq("id", submission_id).execute()
                # Check if submission was found
                if res.data:
                    # Extract first record
                    row = res.data[0]
                    # Decrypt student name or fallback to 'Student'
                    row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Student"
                    # Decrypt student roll or fallback to empty string
                    row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                    # Decrypt student email or fallback to empty string
                    row["student_email"] = ferpa_cipher.decrypt(row.get("student_email_encrypted", "")) or ""
                    # Return decrypted row dictionary
                    return row
            # Catch PostgREST errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase submission by id: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Query Submission table by primary key ID
            s = db.query(Submission).filter(Submission.id == submission_id).first()
            # Return dictionary if found, otherwise None
            return _sub_to_dict(s) if s else None
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # Method to retrieve peer submissions in the same assignment for plagiarism analysis
    def get_peer_submissions(
        self, assignment_id: str, exclude_submission_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query submissions table matching assignment_id
                q = self.client.table("submissions").select("*").eq("assignment_id", assignment_id)
                # Exclude target submission if ID specified
                if exclude_submission_id:
                    # Add not-equal filter on ID
                    q = q.neq("id", exclude_submission_id)
                # Execute query
                res = q.execute()
                # Process records if returned
                if res.data:
                    # Initialize list of peer rows
                    rows = []
                    # Iterate through peer records
                    for row in res.data:
                        # Decrypt peer student name or fallback to 'Peer'
                        row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Peer"
                        # Decrypt peer student roll or fallback to empty string
                        row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                        # Append peer record to results list
                        rows.append(row)
                    # Return decrypted peer rows
                    return rows
            # Catch PostgREST errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase peer submissions: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Query Submission table matching assignment_id
            q = db.query(Submission).filter(Submission.assignment_id == assignment_id)
            # Exclude current submission if ID provided
            if exclude_submission_id:
                # Add inequality filter
                q = q.filter(Submission.id != exclude_submission_id)
            # Return mapped list of peer dictionaries containing text content for comparison
            return [
                # Construct peer summary dictionary
                {
                    # Submission identifier
                    "id": s.id,
                    # Assignment identifier
                    "assignment_id": s.assignment_id,
                    # Decrypted student name
                    "student_name": s.student_name,
                    # Decrypted student roll
                    "student_roll": s.student_roll,
                    # Plain text content for plagiarism comparison
                    "extracted_text": s.extracted_text or s.file_content or "",
                    # Filename of the submission
                    "file_name": s.file_name,
                }
                # Iterate through all peer submission records
                for s in q.all()
            ]
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # Method to insert a new student submission with FERPA-encrypted PII
    def create_submission(
        self,
        # Unique identifier of the assignment
        assignment_id: str,
        # Student full name to encrypt
        student_name: str,
        # Student roll number to encrypt
        student_roll: str,
        # Uploaded file name
        file_name: str,
        # Local disk file path
        file_path: Optional[str] = None,
        # Extracted plain text content
        extracted_text: Optional[str] = None,
        # Optional student email to encrypt
        student_email: Optional[str] = None,
        # Public or static URL to the uploaded file
        file_url: Optional[str] = None,
        # Full content string
        content: Optional[str] = None,
    # Return dictionary summarizing created submission
    ) -> Dict[str, Any]:
        # Method docstring describing FERPA encryption behavior
        """Create a student submission with FERPA-encrypted PII."""
        # Generate random unique submission ID
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        # Encrypt student name using FERPA cipher
        enc_name = ferpa_cipher.encrypt(student_name)
        # Encrypt student roll number using FERPA cipher
        enc_roll = ferpa_cipher.encrypt(student_roll)
        # Encrypt student email if provided, otherwise None
        enc_email = ferpa_cipher.encrypt(student_email) if student_email else None
        # Resolve text content from content or extracted_text
        stored_content = content or extracted_text or ""

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Instantiate Submission ORM model with encrypted fields and initial scores
            sub = Submission(
                # Primary key ID
                id=sub_id,
                # Linked assignment ID
                assignment_id=assignment_id,
                # Encrypted name ciphertext
                student_name_encrypted=enc_name,
                # Encrypted roll ciphertext
                student_roll_encrypted=enc_roll,
                # Encrypted email ciphertext
                student_email_encrypted=enc_email,
                # Document filename
                file_name=file_name,
                # File system path
                file_path=file_path,
                # Static URL
                file_url=file_url,
                # Extracted text body
                extracted_text=extracted_text,
                # Stored content body
                content=stored_content,
                # File content copy
                file_content=stored_content,
                # Initial pending review status
                status="pending",
                # Initial zero similarity score
                similarity_score=0.0,
                # Initial zero AI probability
                ai_content_probability=0.0,
                # Initial zero web plagiarism score
                web_plagiarism_score=0.0,
                # Empty web sources list
                web_sources=[],
            )
            # Add submission record to database session
            db.add(sub)
            # Commit transaction to persist record
            db.commit()

            # Mirror record to Supabase if cloud integration is enabled
            if settings.USE_SUPABASE:
                # Wrap mirror call in try-except block
                try:
                    # Construct mirror payload dictionary
                    payload = {
                        # Submission ID
                        "id": sub_id,
                        # Assignment ID
                        "assignment_id": assignment_id,
                        # Encrypted student name
                        "student_name_encrypted": enc_name,
                        # Encrypted student roll
                        "student_roll_encrypted": enc_roll,
                        # Encrypted student email
                        "student_email_encrypted": enc_email,
                        # Filename
                        "file_name": file_name,
                        # File path
                        "file_path": file_path,
                        # File URL
                        "file_url": file_url,
                        # Extracted text
                        "extracted_text": extracted_text,
                        # Content body
                        "content": stored_content,
                        # Initial status
                        "status": "pending",
                        # Similarity score
                        "similarity_score": 0.0,
                        # AI probability
                        "ai_content_probability": 0.0,
                    }
                    # Insert record into cloud Supabase submissions table
                    self.client.table("submissions").insert(payload).execute()
                # Catch and log cloud mirror errors
                except Exception as exc:
                    # Log debug message
                    logger.debug(f"Supabase submission mirror: {exc}")

            # Return dictionary with decrypted metadata for client response
            return {
                # Submission ID
                "id": sub_id,
                # Assignment ID
                "assignment_id": assignment_id,
                # Plaintext student name
                "student_name": student_name,
                # Plaintext student roll
                "student_roll": student_roll,
                # Document filename
                "file_name": file_name,
                # Current status
                "status": "pending",
            }
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # =========================================================================
    # Local File Storage  (replaces Supabase Storage)
    # =========================================================================

    # Method to save uploaded file bytes to local disk storage with optional cloud mirror
    def upload_file_to_storage(
        self,
        # Raw file byte content
        file_bytes: bytes,
        # Original uploaded file name
        file_name: str,
        # Unique identifier of the assignment
        assignment_id: str,
        # Storage bucket name, defaulting to submissions
        bucket_name: str = "submissions",
        # Optional explicit MIME content type string
        content_type: Optional[str] = None,
    # Return relative URL string or None on failure
    ) -> Optional[str]:
        # Method docstring describing local storage behavior and fallback
        """Save file to local disk under UPLOADS_DIR/<assignment_id>/.

        Returns a relative URL path that the FastAPI static mount can serve.
        Falls back to Supabase Storage if USE_SUPABASE=true.
        """
        # Clean file basename stripping directory traversal characters
        clean_name = os.path.basename(file_name)
        # Generate 8-character unique hexadecimal prefix to prevent collisions
        uid_prefix = uuid.uuid4().hex[:8]
        # Construct assignment-specific destination subdirectory path
        dest_dir = os.path.join(_UPLOADS_DIR, assignment_id)
        # Ensure destination subdirectory exists
        os.makedirs(dest_dir, exist_ok=True)
        # Construct absolute path for the saved file on local disk
        dest_path = os.path.join(dest_dir, f"{uid_prefix}_{clean_name}")

        # Attempt to write bytes to local file
        try:
            # Open target file path in binary write mode
            with open(dest_path, "wb") as fh:
                # Write file bytes to disk
                fh.write(file_bytes)
            # Construct relative URL served by FastAPI static file mount
            rel_url = f"/uploads/{assignment_id}/{uid_prefix}_{clean_name}"
            # Log successful file save
            logger.info(f"Saved {clean_name} → {dest_path}")

            # Best-effort mirror to Supabase cloud storage if enabled
            if settings.USE_SUPABASE:
                # Wrap cloud upload in try-except block
                try:
                    # Guess MIME content type from clean filename
                    ct, _ = mimetypes.guess_type(clean_name)
                    # Upload file to Supabase storage bucket
                    self.client.storage.from_(bucket_name).upload(
                        path=f"{assignment_id}/{uid_prefix}_{clean_name}",
                        file=file_bytes,
                        file_options={"content-type": ct or "application/octet-stream", "upsert": "true"},
                    )
                # Catch and log cloud upload errors
                except Exception as exc:
                    # Log debug message
                    logger.debug(f"Supabase storage mirror: {exc}")

            # Return static relative URL
            return rel_url
        # Catch and log local write errors
        except Exception as exc:
            # Log error details
            logger.error(f"Local storage upload failed for {file_name}: {exc}")
            # Return None on failure
            return None

    # Method to retrieve raw file bytes from local disk, dev server HTTP, or cloud storage
    def download_file_from_storage(
        self,
        # URL or filesystem path to the file
        file_url_or_path: str,
        # Storage bucket name, defaulting to submissions
        bucket_name: str = "submissions",
    # Return file bytes or None if retrieval fails
    ) -> Optional[bytes]:
        # Method docstring describing multi-tier download resolution
        """Download file from local disk or Supabase Storage."""
        # Return None if path or URL is empty
        if not file_url_or_path:
            # Return None
            return None

        # 1. Try local disk first (relative /uploads/... or absolute path)
        local_candidate = file_url_or_path
        # Check if candidate path begins with relative /uploads/ URL prefix
        if local_candidate.startswith("/uploads/"):
            # Resolve to absolute local uploads path
            local_candidate = os.path.join(
                _UPLOADS_DIR, local_candidate[len("/uploads/"):]
            )
        # Check if local candidate is a regular file on disk
        if os.path.isfile(local_candidate):
            # Attempt to read file bytes
            try:
                # Open local file in binary read mode
                with open(local_candidate, "rb") as fh:
                    # Return read bytes
                    return fh.read()
            # Catch local file reading errors
            except Exception as exc:
                # Log warning with error details
                logger.warning(f"Local file read error: {exc}")

        # 2. Try HTTP download (works for both Supabase public URLs and local dev server)
        if file_url_or_path.startswith("http"):
            # Attempt HTTP GET request
            try:
                # Import HTTP client library
                import httpx
                # Fetch remote URL with 15 second timeout
                resp = httpx.get(file_url_or_path, timeout=15.0)
                # Check for successful HTTP status code
                if resp.status_code == 200:
                    # Return response binary content
                    return resp.content
            # Catch HTTP connection errors
            except Exception as exc:
                # Log warning with error details
                logger.warning(f"HTTP download failed: {exc}")

        # 3. Try Supabase Storage if enabled
        if settings.USE_SUPABASE:
            # Wrap cloud storage download in try-except block
            try:
                # Extract bucket-relative storage path from URL
                storage_path = file_url_or_path.split(f"/storage/v1/object/public/{bucket_name}/")[-1]
                # Download bytes from Supabase storage bucket
                return self.client.storage.from_(bucket_name).download(storage_path)
            # Catch cloud download errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase storage download: {exc}")

        # Return None if file could not be retrieved from any source
        return None

    # =========================================================================
    # Assignment Details
    # =========================================================================

    # Method to fetch assignment details including associated rubric
    def get_assignment_details(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query assignments table by ID
                res = self.client.table("assignments").select("*").eq("id", assignment_id).execute()
                # If record found, extract first result
                if res.data:
                    # Extract assignment record dictionary
                    assignment = res.data[0]
                    # Check if assignment has an associated rubric ID
                    rubric_id = assignment.get("rubric_id")
                    # If rubric ID exists, fetch full rubric definition
                    if rubric_id:
                        # Attach nested rubric object
                        assignment["rubric"] = self.get_rubric(rubric_id)
                    # Return assignment dictionary
                    return assignment
            # Catch PostgREST errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase assignment details: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Import Assignment model lazily to avoid circular imports
            from app.models.assignment import Assignment
            # Query Assignment table filtering by ID
            a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            # If assignment found in database, construct dictionary
            if a:
                # Return mapped assignment dictionary
                return {
                    # Assignment identifier
                    "id": a.id,
                    # Linked course identifier
                    "course_id": a.course_id,
                    # Assignment title
                    "title": a.title,
                    # Assignment instructions
                    "description": a.description,
                    # Maximum achievable score
                    "max_score": a.max_score,
                    # Linked rubric identifier
                    "rubric_id": a.rubric_id,
                    # Reference exemplar text
                    "reference_assignment_text": a.reference_assignment_text,
                }
            # Return None if assignment not found
            return None
        # Guarantee database session teardown
        finally:
            # Close database session
            db.close()

    # =========================================================================
    # Evaluation Results
    # =========================================================================

    # Method to persist AI evaluation scores, feedback, integrity checks, and draft grade
    def save_evaluation_results(
        self,
        # Unique identifier of the submission
        submission_id: str,
        # Total calculated score awarded
        overall_score: float,
        # Plagiarism similarity percentage
        similarity_score: float,
        # AI content probability percentage
        ai_content_probability: float,
        # Public web plagiarism score
        web_plagiarism_score: float,
        # List of matched external web sources
        web_sources: List[Dict[str, Any]],
        # Breakdown of individual criteria scores
        criteria_scores: List[Dict[str, Any]],
        # Generated AI feedback text
        ai_feedback: str,
        # Boolean flag indicating whether submission requires instructor escalation
        is_flagged: bool,
    # Return True on success, False on failure
    ) -> bool:
        # Resolve status string based on flag boolean
        status = "flagged" if is_flagged else "graded"

        # Open local database session
        db = SessionLocal()
        # Ensure session teardown
        try:
            # Query Submission table by primary key ID
            sub = db.query(Submission).filter(Submission.id == submission_id).first()
            # If submission exists, update evaluation attributes
            if sub:
                # Update similarity percentage
                sub.similarity_score = similarity_score
                # Update AI content probability
                sub.ai_content_probability = ai_content_probability
                # Update web plagiarism score
                sub.web_plagiarism_score = web_plagiarism_score
                # Update web sources list
                sub.web_sources = web_sources
                # Update status
                sub.status = status
                # Update last modified UTC timestamp
                sub.updated_at = datetime.now(timezone.utc)

            # Generate draft grade primary key
            draft_id = f"draft_{submission_id}"
            # Check for existing draft grade record
            existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == submission_id).first()
            # If draft already exists, update fields
            if existing_draft:
                # Update suggested score
                existing_draft.suggested_score = overall_score
                # Update criteria scores breakdown
                existing_draft.criteria_scores = criteria_scores
                # Update AI feedback text
                existing_draft.ai_feedback = ai_feedback
                # Update draft review status
                existing_draft.status = "flagged" if is_flagged else "pending"
                # Update AI model identifier
                existing_draft.ai_model = settings.GEMINI_MODEL
                # Update modified timestamp
                existing_draft.updated_at = datetime.now(timezone.utc)
            # Otherwise create a new draft grade record
            else:
                # Instantiate new DraftGrade model
                new_draft = DraftGrade(
                    # Primary key ID
                    id=draft_id,
                    # Linked submission ID
                    submission_id=submission_id,
                    # AI-suggested overall score
                    suggested_score=overall_score,
                    # Criteria scores JSON
                    criteria_scores=criteria_scores,
                    # AI feedback string
                    ai_feedback=ai_feedback,
                    # Initial review status
                    status="flagged" if is_flagged else "pending",
                    # Model version string
                    ai_model=settings.GEMINI_MODEL,
                )
                # Add new draft to database session
                db.add(new_draft)

            # Commit local database transaction
            db.commit()
        # Catch and log transaction errors
        except Exception as exc:
            # Log error details
            logger.error(f"Failed to save evaluation results for {submission_id}: {exc}")
            # Return False on failure
            return False
        # Guarantee session teardown
        finally:
            # Close database session
            db.close()

        # Mirror results to Supabase cloud if enabled
        if settings.USE_SUPABASE:
            # Wrap cloud update in try-except block
            try:
                # Update cloud submissions record
                self.client.table("submissions").update({
                    # Update similarity score
                    "similarity_score": similarity_score,
                    # Update AI probability
                    "ai_content_probability": ai_content_probability,
                    # Update web plagiarism score
                    "web_plagiarism_score": web_plagiarism_score,
                    # Update web sources
                    "web_sources": web_sources,
                    # Update status
                    "status": status,
                # Filter by submission primary key
                }).eq("id", submission_id).execute()
                # Upsert cloud draft_grades record
                self.client.table("draft_grades").upsert({
                    # Draft ID
                    "id": f"draft_{submission_id}",
                    # Submission ID
                    "submission_id": submission_id,
                    # Suggested score
                    "suggested_score": overall_score,
                    # Criteria scores
                    "criteria_scores": criteria_scores,
                    # AI feedback text
                    "ai_feedback": ai_feedback,
                    # Status
                    "status": "flagged" if is_flagged else "pending",
                    # Model name
                    "ai_model": settings.GEMINI_MODEL,
                }).execute()
            # Catch cloud mirror errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase eval mirror: {exc}")

        # Return True indicating successful evaluation save
        return True

    # =========================================================================
    # Rubrics
    # =========================================================================

    # Method to retrieve a complete rubric with all nested criteria by ID
    def get_rubric(self, rubric_id: str) -> Optional[Dict[str, Any]]:
        # Check if Supabase cloud integration is enabled
        if settings.USE_SUPABASE:
            # Wrap cloud query in try-except block
            try:
                # Query rubrics table with joined rubric_criteria table
                res = self.client.table("rubrics").select("*, criteria:rubric_criteria(*)").eq("id", rubric_id).execute()
                # Return first record if found
                if res.data:
                    # Return rubric dictionary
                    return res.data[0]
            # Catch PostgREST errors
            except Exception as exc:
                # Log debug message
                logger.debug(f"Supabase rubric: {exc}")

        # Open local database session
        db = SessionLocal()
        # Guarantee session teardown
        try:
            # Query Rubric table by ID
            r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
            # If rubric found, construct nested dictionary
            if r:
                # Return rubric dictionary with nested criteria list
                return {
                    # Rubric unique identifier
                    "id": r.id,
                    # Rubric title
                    "name": r.name,
                    # Associated course identifier
                    "course_id": r.course_id,
                    # Total achievable score across all criteria
                    "total_max_score": r.total_max_score,
                    # List of nested criterion dictionaries
                    "criteria": [
                        # Construct dictionary for each criterion
                        {
                            # Criterion unique identifier
                            "id": c.id,
                            # Criterion name
                            "name": c.name,
                            # Criterion description
                            "description": c.description,
                            # Weight percentage
                            "weight": c.weight,
                            # Maximum points for this criterion
                            "max_score": c.max_score,
                            # UI display sequence order
                            "order_index": c.order_index,
                        }
                        # Iterate through associated criteria
                        for c in r.criteria
                    ],
                }
            # Return None if rubric does not exist
            return None
        # Guarantee session teardown
        finally:
            # Close database session
            db.close()

    # =========================================================================
    # Draft Grades
    # =========================================================================

    # Define method to retrieve a draft grading record for a given submission ID
    def get_draft_grade(self, submission_id: str) -> Optional[Dict[str, Any]]:
        # Check if remote Supabase synchronization is enabled in settings
        if settings.USE_SUPABASE:
            # Wrap remote network operation in a try block to handle failures gracefully
            try:
                # Query the remote draft_grades table filtering by submission_id
                res = self.client.table("draft_grades").select("*").eq("submission_id", submission_id).execute()
                # Check if any record was returned in the response dataset
                if res.data:
                    # Return the first matching draft grade record dictionary
                    return res.data[0]
            # Catch any unexpected exceptions during remote data fetching
            except Exception as exc:
                # Log debug message recording the Supabase draft grade query error
                logger.debug(f"Supabase draft grade: {exc}")

        # Create a new local database session
        db = SessionLocal()
        # Ensure database session cleanup in finally block
        try:
            # Query local DraftGrade table for a record matching the submission_id
            dg = db.query(DraftGrade).filter(DraftGrade.submission_id == submission_id).first()
            # Check if a draft grade entity was found in the local database
            if dg:
                # Return dictionary containing all draft grade fields
                return {
                    # Draft grade unique identifier
                    "id": dg.id,
                    # Associated submission unique identifier
                    "submission_id": dg.submission_id,
                    # AI-suggested numerical score
                    "suggested_score": dg.suggested_score,
                    # Instructor-finalized numerical score
                    "final_score": dg.final_score,
                    # Granular criterion-level breakdown scores
                    "criteria_scores": dg.criteria_scores,
                    # AI-generated qualitative feedback text
                    "ai_feedback": dg.ai_feedback,
                    # Instructor qualitative notes and edits
                    "teacher_feedback": dg.teacher_feedback,
                    # Current review and approval workflow status
                    "status": dg.status,
                    # Name of the AI model that produced the initial evaluation
                    "ai_model": dg.ai_model,
                    # ISO 8601 formatted timestamp of grade approval if present
                    "approved_at": dg.approved_at.isoformat() if dg.approved_at else None,
                }
            # Return None if no draft grade exists for the submission
            return None
        # Guarantee database session termination
        finally:
            # Close the local database session
            db.close()

    # Define method to create or update a draft grade record
    def upsert_draft_grade(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        # Create a new local database session
        db = SessionLocal()
        # Ensure database session cleanup in finally block
        try:
            # Extract the submission identifier from the input payload
            sub_id = draft_data["submission_id"]
            # Query for an existing draft grade record for this submission
            existing = db.query(DraftGrade).filter(DraftGrade.submission_id == sub_id).first()
            # Check if a record already exists in the database
            if existing:
                # Iterate through key-value pairs in the update dictionary
                for k, v in draft_data.items():
                    # Check if attribute exists on model and is not the primary key ID
                    if hasattr(existing, k) and k != "id":
                        # Set attribute on existing record dynamically
                        setattr(existing, k, v)
            # Handle insertion when no record exists yet
            else:
                # Retrieve set of valid column attribute names on DraftGrade model
                allowed = {c.key for c in DraftGrade.__table__.columns}
                # Filter payload dictionary to only include existing column keys
                filtered = {k: v for k, v in draft_data.items() if k in allowed}
                # Add newly instantiated DraftGrade model instance to session
                db.add(DraftGrade(**filtered))
            # Commit database transaction to persist draft grade changes
            db.commit()

            # Check if remote Supabase synchronization is enabled in settings
            if settings.USE_SUPABASE:
                # Wrap remote upsert in try block to catch network issues
                try:
                    # Upsert draft grade record to remote Supabase draft_grades table
                    self.client.table("draft_grades").upsert(draft_data).execute()
                # Catch any unexpected exceptions during remote upsert
                except Exception as exc:
                    # Log debug message recording the remote upsert error
                    logger.debug(f"Supabase draft upsert mirror: {exc}")

            # Return the input draft data dictionary
            return draft_data
        # Guarantee database session termination
        finally:
            # Close the local database session
            db.close()

    # =========================================================================
    # Audit Logs
    # =========================================================================

    # Define method to record an audit log event for compliance and security tracking
    def log_audit(
        # Pass self reference
        self,
        # Display name of the user or system component performing the action
        actor_name: str,
        # Action name describing the operation performed
        action: str,
        # Type of entity affected (e.g. course, submission, grade)
        entity_type: str,
        # Unique identifier of the affected entity
        entity_id: str,
        # Optional metadata dictionary providing additional context
        details: Optional[Dict[str, Any]] = None,
        # Optional unique identifier of the user who initiated the action
        actor_id: Optional[str] = None,
        # Optional client IP address from which the request originated
        ip_address: Optional[str] = None,
    # Return type is a dictionary representing the persisted audit log entry
    ) -> Dict[str, Any]:
        # Generate a unique audit log ID prefixed with audit_
        log_id = f"audit_{uuid.uuid4().hex[:12]}"
        # Construct audit log payload dictionary
        payload = {
            # Unique log event identifier
            "id": log_id,
            # User ID of the actor
            "actor_id": actor_id,
            # Name of the actor
            "actor_name": actor_name,
            # Action type string
            "action": action,
            # Entity domain category
            "entity_type": entity_type,
            # Targeted entity identifier
            "entity_id": entity_id,
            # Detailed event metadata or empty dictionary
            "details": details or {},
            # Originating network IP address
            "ip_address": ip_address,
            # UTC timestamp formatted in ISO 8601 standard
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Create a new local database session
        db = SessionLocal()
        # Wrap audit insertion in try block to log errors without breaking caller flow
        try:
            # Instantiate AuditLog SQLAlchemy model instance
            log_record = AuditLog(
                # Set record unique ID
                id=log_id,
                # Set actor user ID
                actor_id=actor_id,
                # Set actor display name
                actor_name=actor_name,
                # Set action string
                action=action,
                # Set entity category
                entity_type=entity_type,
                # Set entity ID
                entity_id=entity_id,
                # Set metadata JSON dictionary
                details=details or {},
                # Set client IP address
                ip_address=ip_address,
            )
            # Add audit record to database session
            db.add(log_record)
            # Commit transaction to persist audit record immediately
            db.commit()

            # Check if remote Supabase synchronization is enabled in settings
            if settings.USE_SUPABASE:
                # Wrap remote insert in try block to catch network issues
                try:
                    # Insert audit record to remote Supabase audit_logs table
                    self.client.table("audit_logs").insert(payload).execute()
                # Catch any unexpected exceptions during remote insert
                except Exception as exc:
                    # Log debug message recording the remote audit mirror error
                    logger.debug(f"Supabase audit mirror: {exc}")

            # Return the generated audit log payload dictionary
            return payload
        # Catch any database or processing error during audit log recording
        except Exception as exc:
            # Log error message reporting audit log failure
            logger.error(f"Audit log write failed: {exc}")
            # Return payload even if persistence failed to avoid crashing the caller
            return payload
        # Guarantee database session termination
        finally:
            # Close the local database session
            db.close()


# Instantiate a global singleton instance of SupabaseService for application-wide use
supabase_service = SupabaseService()

