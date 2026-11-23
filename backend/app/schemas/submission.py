# Module docstring explaining that this file defines submission data models and response schemas
"""Submission schemas."""

# Import standard mimetypes module for MIME type resolution
import mimetypes
# Import datetime utility for timestamp handling
from datetime import datetime
# Import typing utilities for lists and optional values
from typing import List, Optional
# Import Pydantic base model, field constructor, configuration dictionary, and validator
from pydantic import BaseModel, Field, ConfigDict, model_validator
# Import VerismBaseModel base class supporting dual camelCase and snake_case keys
from app.schemas.base import VerismBaseModel


# Schema for validating incoming requests to create a single student submission
class SubmissionCreate(BaseModel):
    # Optional identifier of the assignment associated with this submission
    assignment_id: Optional[str] = None
    # Student's plaintext full name to be FERPA encrypted upon save
    student_name: str
    # Student's plaintext roll number to be FERPA encrypted upon save
    student_roll: str
    # Optional student email address to be FERPA encrypted upon save
    student_email: Optional[str] = None
    # Extracted plain text content from the uploaded student document
    extracted_text: Optional[str] = None


# Schema for returning submission summary data in API list responses
class SubmissionResponse(VerismBaseModel):
    # Unique string identifier for the submission
    id: str
    # Identifier of the assignment this submission belongs to
    assignment_id: str
    # Decrypted student full name for authorized instructor view
    student: str  # Decrypted student name
    # Decrypted student roll or registration number
    roll: str     # Decrypted roll
    # Optional unique student database ID if linked to a roster record
    student_id: Optional[str] = None
    # Original filename of the uploaded submission document
    file_name: str
    # Normalized alias for filename
    filename: Optional[str] = None
    # Inferred or persisted document file format type
    file_type: str = "pdf"
    # Internet media MIME type of the document
    mime_type: str = "application/pdf"
    # Current workflow status (e.g., ready, queued, graded, approved)
    status: str = "unprocessed"
    # Score awarded for the submission, None when ungraded
    score: Optional[float] = None
    # Maximum possible score for the assignment
    max_score: Optional[float] = None
    # Peer similarity percentage score, None until similarity check runs
    similarity: Optional[float] = None
    # AI generated content probability percentage, None until evaluation runs
    ai_content: Optional[float] = Field(default=None, alias="aiContent")
    # Public web search plagiarism percentage, None until check runs
    web_plagiarism: Optional[float] = Field(default=None, alias="webPlagiarism")
    # Optional download URL or storage path for the original file
    file_url: Optional[str] = None
    # Optional list of criterion scores breakdown dictionaries
    criteria_scores: Optional[List[dict]] = None
    # Indicates whether the submission could not be matched to an enrolled student
    is_unmatched: Optional[bool] = False
    # Optional qualitative feedback summary for the submission
    feedback: Optional[str] = None
    # Optional full integrity audit and plagiarism report dictionary
    plagiarism_report: Optional[dict] = None
    # Timestamp when the submission was recorded in the database
    created_at: Optional[datetime] = None

    # Model validator populating filename and mime_type automatically
    @model_validator(mode="after")
    def populate_file_metadata(self) -> "SubmissionResponse":
        # Check if filename is missing but file_name is present
        if not self.filename and self.file_name:
            # Set filename to file_name
            self.filename = self.file_name
        # Guess MIME type based on file name if default
        if self.file_name:
            # Resolve MIME type tuple from standard registry
            guessed, _ = mimetypes.guess_type(self.file_name)
            # If MIME type successfully identified
            if guessed:
                # Update mime_type attribute
                self.mime_type = guessed
                # Update file_type to subtype segment
                self.file_type = guessed.split("/")[-1]
        # Return self instance after validation
        return self


# Schema providing full detailed submission content, text excerpts, and sources
class SubmissionDetailResponse(SubmissionResponse):
    # Full plain text content extracted from the student document
    extracted_text: Optional[str] = None
    # Content body alias for UI viewing
    content: Optional[str] = None
    # Overlapping passage or sentence snippet matched with another student
    matching_phrase: Optional[str] = None
    # Detailed list of evaluated rubric criteria scores and justifications
    criteria_scores: List[dict] = Field(default_factory=list)
    # AI-generated qualitative feedback and rubric justification
    ai_feedback: Optional[str] = None
    # Instructor override notes and qualitative feedback
    teacher_feedback: Optional[str] = None
    # List of matched external web sources with URLs and snippets
    web_sources: List[dict] = Field(default_factory=list, alias="webSources")
    # List of specific phrases flagged as plagiarized
    plagiarised_words: List[str] = Field(default_factory=list, alias="plagiarisedWords")


# Schema returning batch upload results for standard bulk ZIP submissions
class BatchUploadResponse(VerismBaseModel):
    # Unique string identifier for the batch upload operation
    batch_id: str
    # Total count of files found and processed within the archive
    total_files: int
    # List of uploaded file names extracted from the batch
    uploaded_files: List[str]
    # List of created submission summary response objects
    submissions: List[SubmissionResponse]


# Schema representing an individual item parsed from a classroom bulk upload
class ClassroomBatchUploadItem(VerismBaseModel):
    # Unique identifier of the uploaded submission item
    id: str
    # Filename of the uploaded document
    file_name: str
    # Normalized alias for filename
    filename: Optional[str] = None
    # Detected file extension type
    file_type: str = "pdf"
    # Document MIME type
    mime_type: str = "application/pdf"
    # Optional matched student database identifier
    student_id: Optional[str] = None
    # Optional student roll number extracted from filename or roster match
    roll_number: Optional[str] = None
    # Optional student full name matched from the classroom roster
    student_name: Optional[str] = None
    # Matching status indicating whether the item is queued or unmatched
    status: str  # 'queued' or 'unmatched'
    # Storage URL or file path for the submission
    file_url: Optional[str] = None

    # Model validator populating filename and mime_type automatically
    @model_validator(mode="after")
    def populate_batch_item_metadata(self) -> "ClassroomBatchUploadItem":
        # Check if filename is missing but file_name is present
        if not self.filename and self.file_name:
            # Set filename to file_name
            self.filename = self.file_name
        # Guess MIME type based on file name if default
        if self.file_name:
            # Resolve MIME type tuple from standard registry
            guessed, _ = mimetypes.guess_type(self.file_name)
            # If MIME type successfully identified
            if guessed:
                # Update mime_type attribute
                self.mime_type = guessed
                # Update file_type to subtype segment
                self.file_type = guessed.split("/")[-1]
        # Return self instance after validation
        return self


# Schema returning categorized queued versus unmatched items from classroom bulk upload
class ClassroomBatchUploadResponse(VerismBaseModel):
    # Unique identifier of the background batch processing job
    batch_job_id: str
    # Total count of submission files uploaded in the batch
    total: int
    # List of submissions successfully resolved and queued for evaluation
    queued_submissions: List[ClassroomBatchUploadItem] = Field(default_factory=list)
    # List of submissions requiring manual instructor student assignment
    unmatched_submissions: List[ClassroomBatchUploadItem] = Field(default_factory=list)
    # Initial status of the batch job, defaulting to queued
    status: str = "queued"


# Schema for manually resolving an unmatched submission by assigning a student ID
class AssignStudentRequest(BaseModel):
    # Unique database identifier of the student to link to the submission
    student_id: str


