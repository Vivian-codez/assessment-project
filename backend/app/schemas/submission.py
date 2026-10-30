# Module docstring explaining that this file defines submission data models and response schemas
"""Submission schemas."""

# Import datetime utility for timestamp handling
from datetime import datetime
# Import typing utilities for lists and optional values
from typing import List, Optional
# Import Pydantic base model, field constructor, and configuration dictionary
from pydantic import BaseModel, Field, ConfigDict


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
class SubmissionResponse(BaseModel):
    # Enable reading attributes from ORM database models and supporting field aliases
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

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
    # Current workflow status (e.g., queued, graded, reviewed, flagged)
    status: str
    # Score awarded for the submission, defaulting to 0.0
    score: float = 0.0
    # Maximum possible score for the assignment, defaulting to 100.0
    max_score: float = 100.0
    # Peer similarity percentage score, defaulting to 0.0
    similarity: float = 0.0
    # AI generated content probability percentage, aliased to aiContent
    ai_content: float = Field(default=0.0, alias="aiContent")
    # Public web search plagiarism percentage, aliased to webPlagiarism
    web_plagiarism: float = Field(default=0.0, alias="webPlagiarism")
    # Optional download URL or storage path for the original file
    file_url: Optional[str] = None
    # Optional list of criterion scores breakdown dictionaries
    criteria_scores: Optional[List[dict]] = None
    # Optional qualitative feedback summary for the submission
    feedback: Optional[str] = None
    # Optional full integrity audit and plagiarism report dictionary
    plagiarism_report: Optional[dict] = None
    # Timestamp when the submission was recorded in the database
    created_at: datetime


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
class BatchUploadResponse(BaseModel):
    # Unique string identifier for the batch upload operation
    batch_id: str
    # Total count of files found and processed within the archive
    total_files: int
    # List of uploaded file names extracted from the batch
    uploaded_files: List[str]
    # List of created submission summary response objects
    submissions: List[SubmissionResponse]


# Schema representing an individual item parsed from a classroom bulk upload
class ClassroomBatchUploadItem(BaseModel):
    # Unique identifier of the uploaded submission item
    id: str
    # Filename of the uploaded document
    file_name: str
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


# Schema returning categorized queued versus unmatched items from classroom bulk upload
class ClassroomBatchUploadResponse(BaseModel):
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


