"""FERPA/GDPR Anonymization and Pseudonymization Pipeline Service."""

import re
from typing import Dict, Tuple
from app.core.security import ferpa_cipher
from app.core.logging import logger


class FerpaService:
    """Ensures no student Personally Identifiable Information (PII) is exposed

    to external LLMs or third-party APIs during AI grading or similarity
    analysis.
    """

    def prepare_for_ai_evaluation(
        self,
        submission_id: str,
        student_name: str,
        student_roll: str,
        student_email: str,
        text_content: str,
    ) -> Tuple[str, str]:
        """Returns (pseudo_id, sanitized_text) where:

        - pseudo_id: Deterministic anonymous token like 'STUDENT_B7A4C1'
        - sanitized_text: Text stripped of student name, roll number, and emails
        """
        pseudo_id = ferpa_cipher.pseudonymize(submission_id)

        sanitized_text = text_content or ""

        # Remove explicit student name if found
        if student_name and len(student_name) > 2:
            sanitized_text = re.sub(re.escape(student_name), "[STUDENT_NAME]", sanitized_text, flags=re.IGNORECASE)

        # Remove explicit roll number if found
        if student_roll and len(student_roll) > 2:
            sanitized_text = re.sub(re.escape(student_roll), "[STUDENT_ROLL]", sanitized_text, flags=re.IGNORECASE)

        # Remove emails via regex
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        sanitized_text = re.sub(email_pattern, "[STUDENT_EMAIL]", sanitized_text)

        # Remove phone numbers
        phone_pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        sanitized_text = re.sub(phone_pattern, "[PHONE_REDACTED]", sanitized_text)

        logger.debug(f"[FERPA] Pseudonymized submission {submission_id} -> {pseudo_id} for AI analysis")
        return pseudo_id, sanitized_text


ferpa_service = FerpaService()
