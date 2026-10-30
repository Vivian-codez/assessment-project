# Module docstring explaining that this file implements the FERPA/GDPR anonymization and pseudonymization pipeline
"""FERPA/GDPR Anonymization and Pseudonymization Pipeline Service."""

# Import regular expressions module for sanitizing pattern matches
import re
# Import typing utilities for dictionary mappings and tuples
from typing import Dict, Tuple
# Import the shared FERPA cipher instance for pseudonymization and encryption
from app.core.security import ferpa_cipher
# Import system logger for diagnostic recording
from app.core.logging import logger


# Class responsible for anonymizing student submissions prior to external AI LLM processing
class FerpaService:
    # Class docstring explaining compliance guarantee against PII exposure
    """Ensures no student Personally Identifiable Information (PII) is exposed

    to external LLMs or third-party APIs during AI grading or similarity
    analysis.
    """

    # Method that takes raw student metadata and returns an anonymous token and sanitized text
    def prepare_for_ai_evaluation(
        self,
        # The database primary key of the submission
        submission_id: str,
        # The student's full name to be redacted
        student_name: str,
        # The student's roll or registration number to be redacted
        student_roll: str,
        # The student's email address to be redacted
        student_email: str,
        # The raw text content of the assignment paper
        text_content: str,
    # Return type annotation specifying a tuple of anonymous ID string and sanitized text string
    ) -> Tuple[str, str]:
        # Method docstring detailing the returned pseudonym ID and sanitized content
        """Returns (pseudo_id, sanitized_text) where:

        - pseudo_id: Deterministic anonymous token like 'STUDENT_B7A4C1'
        - sanitized_text: Text stripped of student name, roll number, and emails
        """
        # Generate deterministic pseudonymous student token using HMAC from submission identifier
        pseudo_id = ferpa_cipher.pseudonymize(submission_id)

        # Fallback to empty string if text content is None
        sanitized_text = text_content or ""

        # Check if a non-trivial student name is provided
        if student_name and len(student_name) > 2:
            # Replace case-insensitive instances of student name with placeholder token
            sanitized_text = re.sub(re.escape(student_name), "[STUDENT_NAME]", sanitized_text, flags=re.IGNORECASE)

        # Check if a non-trivial student roll number is provided
        if student_roll and len(student_roll) > 2:
            # Replace case-insensitive instances of student roll number with placeholder token
            sanitized_text = re.sub(re.escape(student_roll), "[STUDENT_ROLL]", sanitized_text, flags=re.IGNORECASE)

        # Define regular expression matching email addresses
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        # Replace detected email addresses with placeholder token
        sanitized_text = re.sub(email_pattern, "[STUDENT_EMAIL]", sanitized_text)

        # Define regular expression matching domestic and international phone numbers
        phone_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        # Replace detected phone numbers with redacted placeholder token
        sanitized_text = re.sub(phone_pattern, "[PHONE_REDACTED]", sanitized_text)

        # Log debug message recording successful pseudonymization and redaction
        logger.debug(f"[FERPA] Pseudonymized submission {submission_id} -> {pseudo_id} for AI analysis")
        # Return tuple containing anonymous token and redacted clean text
        return pseudo_id, sanitized_text


# Instantiate singleton instance of FerpaService for dependency injection across the backend
ferpa_service = FerpaService()
