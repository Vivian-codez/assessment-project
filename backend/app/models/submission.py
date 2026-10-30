"""Submission database model with FERPA/GDPR encryption handlers."""

# Import datetime class for UTC timestamp tracking
from datetime import datetime
# Import SQLAlchemy Column and data types (String, Float, DateTime, ForeignKey, Text, JSON)
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON
# Import relationship construct to map links between Submission, Assignment, and DraftGrade
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database
from app.core.database import Base
# Import global FERPA encryption handler to transparently encrypt and decrypt student PII
from app.core.security import ferpa_cipher


# Database model representing student assignment submissions and integrity evaluation records
class Submission(Base):
    # Specify target physical table name in PostgreSQL
    __tablename__ = "submissions"

    # Alphanumeric unique identifier for submission acting as primary key
    id = Column(String(64), primary_key=True, index=True)
    # Foreign key referencing parent assignment (cascades deletions when assignment is deleted)
    assignment_id = Column(String(64), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional classroom identifier foreign association
    classroom_id = Column(String(64), ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True, index=True)
    # Optional enrolled student identifier foreign association
    student_id = Column(String(64), ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)

    # FERPA/GDPR Encrypted Student Information (Nullable for unmatched submissions)
    # Student legal full name stored encrypted with AES-256
    student_name_encrypted = Column(Text, nullable=True)
    # Student institutional roll number stored encrypted with AES-256
    student_roll_encrypted = Column(Text, nullable=True)
    # Student email address stored encrypted with AES-256
    student_email_encrypted = Column(Text, nullable=True)

    # File and Submission Metadata
    # Original filename of the uploaded student submission document
    file_name = Column(String(255), nullable=False)
    # Storage filesystem relative or absolute path on disk
    file_path = Column(String(512), nullable=True)
    # Public or signed download URL for client frontend access
    file_url = Column(String(1024), nullable=True)
    # File format type (defaults to 'pdf')
    file_type = Column(String(64), default="pdf")
    # Clean text extracted from uploaded document by parsing pipeline
    extracted_text = Column(Text, nullable=True)
    # Raw text content alias stored in database
    content = Column(Text, nullable=True)  # Raw text or extracted text alias for database
    # Raw file content (plaintext code or base64 binary) stored directly in database
    file_content = Column(Text, nullable=True)  # Raw file content (text or base64) stored directly in database

    # Plagiarism / Similarity & AI Indicators
    # Highest percentage similarity score found with any other peer submission
    similarity_score = Column(Float, default=0.0)  # Highest similarity % found with any peer
    # Estimated probability percentage (0 to 100%) that the submission was AI-generated
    ai_content_probability = Column(Float, default=0.0)  # 0 to 100%
    # Percentage match score against public web and online academic sources
    web_plagiarism_score = Column(Float, default=0.0)  # 0 to 100% public web plagiarism
    # JSON array containing web source matches [{'url': ..., 'title': ..., 'match_pct': ...}]
    web_sources = Column(JSON, default=list)  # [{'url': ..., 'title': ..., 'match_pct': ...}]

    # Status: pending, processing, flagged, graded, approved
    # Processing and evaluation status string indexed for queue filtering
    status = Column(String(32), default="pending", index=True)

    # UTC timestamp when the student submission was uploaded
    created_at = Column(DateTime, default=datetime.utcnow)
    # UTC timestamp when the submission record was last updated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    # Many-to-one relationship mapping the parent assignment
    assignment = relationship("Assignment", back_populates="submissions")
    # Many-to-one relationship mapping parent classroom
    classroom = relationship("Classroom", back_populates="submissions")
    # Many-to-one relationship mapping enrolled student
    student = relationship("Student", back_populates="submissions")
    # One-to-one relationship mapping the generated draft grade evaluation (cascades on delete)
    draft_grade = relationship("DraftGrade", back_populates="submission", uselist=False, cascade="all, delete-orphan")

    # Transparent FERPA Decrypt/Encrypt Property Accessors
    # Getter property returning decrypted student full name
    @property
    def student_name(self) -> str:
        # Decrypt ciphertext using ferpa_cipher or return empty string
        return ferpa_cipher.decrypt(self.student_name_encrypted) or ""

    # Setter property encrypting plaintext student full name before database write
    @student_name.setter
    def student_name(self, value: str):
        # Encrypt plaintext name with ferpa_cipher and assign to encrypted column
        self.student_name_encrypted = ferpa_cipher.encrypt(value)

    # Getter property returning decrypted student roll number
    @property
    def student_roll(self) -> str:
        # Decrypt ciphertext using ferpa_cipher or return empty string
        return ferpa_cipher.decrypt(self.student_roll_encrypted) or ""

    # Setter property encrypting plaintext student roll number before database write
    @student_roll.setter
    def student_roll(self, value: str):
        # Encrypt plaintext roll number with ferpa_cipher and assign to encrypted column
        self.student_roll_encrypted = ferpa_cipher.encrypt(value)

    # Getter property returning decrypted student email address
    @property
    def student_email(self) -> str:
        # Decrypt ciphertext using ferpa_cipher or return empty string
        return ferpa_cipher.decrypt(self.student_email_encrypted) or ""

    # Setter property encrypting plaintext student email address before database write
    @student_email.setter
    def student_email(self, value: str):
        # Encrypt plaintext email with ferpa_cipher and assign to encrypted column
        self.student_email_encrypted = ferpa_cipher.encrypt(value)
