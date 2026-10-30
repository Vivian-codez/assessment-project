# Module docstring explaining the filename parsing rules and student resolution logic
"""Filename Parser & Student Resolver Service.

Extracts roll numbers from common academic naming conventions:
- Prefix: 102_Lab1.pdf, 12_OOP_Lab.py, 201-JohnDoe.pdf
- Infix: Alice_Roll102.py, Roll_12_Alice.pdf, CS301_201_Lab.pdf
- Suffix: assignment_102.pdf, CS101-12.pdf, Alice_102.py
- Standalone: 102.cpp, 201.py

Resolves each filename against enrolled students in the Supabase `students` table
for a given `classroom_id`. If no match is found, marks record as 'unmatched'.
"""

# Import os module for extracting path basenames and extensions
import os
# Import re module for regex pattern matching
import re
# Import typing utilities for dicts, lists, optionals, tuples, and any types
from typing import Dict, List, Optional, Tuple, Any

# Import Supabase client stub/instance for database operations
from app.core.supabase import supabase
from app.core.database import SessionLocal
from app.models.student import Student
from app.core.config import settings
from sqlalchemy import func
# Import system logger for logging resolution events and errors
from app.core.logging import logger


# Function to extract student roll numbers from arbitrary file naming patterns
def extract_roll_number(filename: str) -> Optional[str]:
    # Function docstring listing supported naming patterns
    """Extracts student roll number from typical academic naming conventions.

    Supports:
    - Explicit tags: Roll_12_Alice.pdf, Alice_Roll102.py, Roll#102.pdf
    - Leading prefix: 12_OOP_Lab.py, 102_Lab1.pdf, 201-John.pdf
    - Standalone number: 102.cpp, 201.py
    - Code/assignment infix: CS101-12.pdf, assignment_102.pdf, lab1_102.pdf
    - Trailing suffix: Alice_102.pdf, Bob-102.docx
    - Separated infix: CS301_201_Lab.pdf
    """
    # Guard against empty or None filename input
    if not filename:
        # Return None if no filename provided
        return None

    # Strip directory path to isolate the file name
    base_name = os.path.basename(filename)
    # Strip file extension and remove surrounding whitespace
    stem = os.path.splitext(base_name)[0].strip()

    # Guard against empty stem
    if not stem:
        # Return None if filename stem is blank
        return None

    # Priority 1: Search for explicit roll keywords (e.g. Roll_12, Roll12, Roll#12, rollno_12, Alice_Roll102)
    m = re.search(r'(?i)(?:roll(?:_?no|num|number)?|rn)[_\s#-]*([a-zA-Z0-9]+)', stem)
    # Check if explicit keyword regex matched
    if m:
        # Extract and strip the captured group value
        val = m.group(1).strip()
        # Verify the captured value is non-empty
        if val:
            # Return captured roll number
            return val

    # Priority 2: Check for leading prefix digits followed by a delimiter (e.g. 12_OOP_Lab.py, 102_Lab1.pdf)
    m = re.match(r'^(\d+)[_\-\s.]', stem)
    # Check if leading prefix regex matched
    if m:
        # Return the captured leading numeric digits
        return m.group(1)

    # Priority 3: Check if the entire stem is a standalone numeric string (e.g. 102.cpp, 201.py)
    if stem.isdigit():
        # Return stem as the roll number
        return stem

    # Priority 4: Check for course code or assignment prefix with hyphen/underscore followed by number
    m = re.search(r'(?i)(?:[a-z]{2,}\d*|[a-z]+)[_-]+(\d+)(?:[_\-\s.]|$)', stem)
    # Check if assignment prefix regex matched
    if m:
        # Return captured numeric roll digits
        return m.group(1)

    # Priority 5: Check for trailing roll number at the end of the stem (e.g. Alice_102.pdf)
    m = re.search(r'[_\-\s](\d+)$', stem)
    # Check if trailing suffix regex matched
    if m:
        # Return captured trailing roll digits
        return m.group(1)

    # Priority 6: Check for infix number surrounded by delimiters (e.g. CS301_201_Lab.pdf)
    m = re.search(r'[_\-\s](\d+)[_\-\s]', stem)
    # Check if infix regex matched
    if m:
        # Return captured infix roll digits
        return m.group(1)

    # Return None if no roll number pattern matched the filename
    return None


# Service class for resolving student identities from filenames against classroom rosters
class StudentResolverService:
    # Class docstring describing Supabase student resolution
    """Resolves filenames to enrolled students in Supabase."""

    # Initializer configuring the Supabase client
    def __init__(self):
        # Store database client reference
        self.client = supabase

    # Method to query all enrolled students for a given classroom
    def get_classroom_students(self, classroom_id: str) -> List[Dict[str, Any]]:
        # 1. Primary: Query local database via SQLAlchemy
        try:
            with SessionLocal() as db:
                db_students = db.query(Student).filter(Student.classroom_id == classroom_id).all()
                if db_students:
                    return [
                        {
                            "id": s.id,
                            "classroom_id": s.classroom_id,
                            "roll_number": s.roll_number,
                            "full_name": s.full_name,
                            "email": s.email,
                        }
                        for s in db_students
                    ]
        except Exception as db_err:
            logger.debug(f"Local student query notice for classroom {classroom_id}: {db_err}")

        # 2. Optional: Cloud query fallback if USE_SUPABASE is true
        if settings.USE_SUPABASE:
            try:
                res = (
                    self.client.table("students")
                    .select("id, classroom_id, roll_number, full_name, email")
                    .eq("classroom_id", classroom_id)
                    .execute()
                )
                return res.data or []
            except Exception as e:
                logger.error(f"Error fetching students for classroom {classroom_id} from cloud: {e}")

        return []

    # Method to construct an in-memory hash index for rapid O(1) student lookups
    def build_roster_index(self, students: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # Method docstring describing index construction
        """Builds an index of students by exact and normalized roll numbers for O(1) lookup."""
        # Initialize empty dictionary for fast roll lookups
        index: Dict[str, Dict[str, Any]] = {}
        # Iterate over each student record in the classroom roster
        for s in students:
            # Extract and strip roll number string
            roll = str(s.get("roll_number", "")).strip()
            # Skip records without a valid roll number
            if not roll:
                # Continue to next student
                continue
            # Map exact roll number
            index[roll] = s
            # Map lowercase roll number
            index[roll.lower()] = s
            # Map roll number with leading zeros stripped
            index[roll.lstrip("0")] = s
            # Create alphanumeric normalized roll string without punctuation
            norm = re.sub(r"[^a-zA-Z0-9]", "", roll).lower()
            # If normalized roll is non-empty, add to index
            if norm:
                # Map normalized key to student record
                index[norm] = s
        # Return completed roster lookup dictionary
        return index

    # Method to fetch students and construct the roster lookup index in one step
    def get_classroom_roster_index(self, classroom_id: str) -> Dict[str, Dict[str, Any]]:
        # Method docstring describing combined fetch and index behavior
        """Fetches classroom students and returns a normalized roster lookup index."""
        # Fetch all enrolled students for the classroom
        students = self.get_classroom_students(classroom_id)
        # Build and return index from fetched student records
        return self.build_roster_index(students)

    # Method to resolve an individual student record by classroom and roll number
    def resolve_student_by_roll(
        self,
        # Unique identifier of the classroom
        classroom_id: str,
        # Target roll number to look up
        roll_number: str,
        # Optional pre-built roster index for cached lookups
        roster_index: Optional[Dict[str, Dict[str, Any]]] = None,
    # Return type annotation for student dictionary or None
    ) -> Optional[Dict[str, Any]]:
        # Guard against empty roll number or classroom ID
        if not roll_number or not classroom_id:
            return None

        # Check if pre-built roster index is available for fast lookup
        if roster_index:
            clean_roll = roll_number.strip()
            if clean_roll in roster_index:
                return roster_index[clean_roll]
            if clean_roll.lower() in roster_index:
                return roster_index[clean_roll.lower()]
            if clean_roll.lstrip("0") in roster_index:
                return roster_index[clean_roll.lstrip("0")]

        # Query local database directly if not resolved via preloaded index
        clean_roll = roll_number.strip().lower()
        try:
            with SessionLocal() as db:
                st = (
                    db.query(Student)
                    .filter(
                        Student.classroom_id == classroom_id,
                        func.lower(Student.roll_number) == clean_roll,
                    )
                    .first()
                )
                if st:
                    return {
                        "id": st.id,
                        "classroom_id": st.classroom_id,
                        "roll_number": st.roll_number,
                        "full_name": st.full_name,
                        "email": st.email,
                    }
        except Exception as db_err:
            logger.debug(f"Local student roll query notice: {db_err}")

        # Cloud fallback if USE_SUPABASE
        if settings.USE_SUPABASE:
            try:
                res = (
                    self.client.table("students")
                    .select("id, classroom_id, roll_number, full_name, email")
                    .eq("classroom_id", classroom_id)
                    .eq("roll_number", roll_number.strip())
                    .execute()
                )
                if res.data:
                    return res.data[0]

                res_ilike = (
                    self.client.table("students")
                    .select("id, classroom_id, roll_number, full_name, email")
                    .eq("classroom_id", classroom_id)
                    .ilike("roll_number", roll_number.strip())
                    .execute()
                )
                if res_ilike.data:
                    return res_ilike.data[0]
            except Exception as e:
                logger.error(f"Error querying student by roll in cloud: {e}")

        return None

    # Method to parse a filename, extract the roll number, and resolve the enrolled student
    def resolve_submission_file(
        self,
        # Classroom identifier
        classroom_id: str,
        # Uploaded file name
        filename: str,
        # Optional pre-built roster index
        roster_index: Optional[Dict[str, Dict[str, Any]]] = None,
    # Return tuple of student_id, status, student_record, and extracted_roll
    ) -> Tuple[Optional[str], str, Optional[Dict[str, Any]], Optional[str]]:
        # Method docstring describing return tuple structure
        """Parses filename roll number and resolves to student_id.

        Returns:
            Tuple of (student_id, status, student_record, extracted_roll)
            where status is 'queued' if matched or 'unmatched' if no matching enrolled student.
        """
        # Extract roll number from the filename
        extracted_roll = extract_roll_number(filename)
        # Check if roll number extraction failed
        if not extracted_roll:
            # Return unmatched status tuple
            return None, "unmatched", None, None

        # Resolve student record using extracted roll number
        student = self.resolve_student_by_roll(classroom_id, extracted_roll, roster_index=roster_index)
        # Check if matching student was found and has a valid ID
        if student and student.get("id"):
            # Return queued status tuple with student details
            return str(student["id"]), "queued", student, extracted_roll

        # Return unmatched status tuple if roll could not be mapped to an enrolled student
        return None, "unmatched", None, extracted_roll


# Instantiate singleton student resolver instance for application-wide use
student_resolver = StudentResolverService()
