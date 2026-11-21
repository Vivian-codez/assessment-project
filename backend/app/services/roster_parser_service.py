"""Multi-Format Roster Parser Service supporting CSV, XLSX, XLS, PDF, DOCX, TXT, and Images using Heuristics and Gemini LLM Extraction."""

import csv
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


class RosterParserService:
    """Service to parse student rosters from any file format."""

    def __init__(self):
        self.client = None
        if _GENAI_AVAILABLE and getattr(settings, "GEMINI_API_KEY", None):
            try:
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client for RosterParserService: {e}")

    def parse_roster_file(self, filename: str, content: bytes) -> List[Dict[str, str]]:
        """Accepts any file format, extracts text or tables, and extracts normalized student records."""
        ext = filename.lower().split(".")[-1] if "." in filename else "txt"
        records: List[Dict[str, str]] = []

        try:
            if ext in {"csv", "tsv", "txt"}:
                records = self._parse_delimited_or_text(content, ext)
            elif ext in {"xlsx", "xls"}:
                records = self._parse_excel(content)
            elif ext == "pdf":
                records = self._parse_pdf(content)
            elif ext in {"docx", "doc"}:
                records = self._parse_docx(content)
            elif ext in {"png", "jpg", "jpeg", "webp"}:
                records = self._parse_image(content, ext)
            elif ext == "zip":
                records = self._parse_zip(content)
            else:
                records = self._parse_delimited_or_text(content, "txt")
        except Exception as e:
            logger.error(f"Error parsing roster file {filename}: {e}")

        # If zero records extracted or incomplete, try LLM fallback if content text is available
        if not records and ext not in {"png", "jpg", "jpeg", "webp"}:
            extracted_text = self._extract_raw_text(filename, content, ext)
            if extracted_text and len(extracted_text.strip()) > 10:
                records = self._extract_with_gemini_text(extracted_text)

        # Normalize and deduplicate by roll number
        normalized: List[Dict[str, str]] = []
        seen_rolls = set()
        for r in records:
            roll = str(r.get("roll_number", "")).strip()
            name = str(r.get("full_name", "")).strip()
            email = str(r.get("email", "")).strip()

            if not roll and not name:
                continue

            # Fallback for missing roll number
            if not roll and name:
                roll = f"AUTO-{len(normalized) + 1:03d}"

            # Fallback for missing name
            if not name and roll:
                name = f"Student {roll}"

            roll_key = roll.lower()
            if roll_key in seen_rolls:
                continue
            seen_rolls.add(roll_key)

            normalized.append({
                "roll_number": roll,
                "full_name": name,
                "email": email,
            })

        return normalized

    def _parse_delimited_or_text(self, content: bytes, ext: str) -> List[Dict[str, str]]:
        """Parses CSV, TSV, or comma/tab separated text files."""
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        # Try standard CSV parsing first
        for delimiter in [",", "\t", ";", "|"]:
            try:
                reader = csv.reader(io.StringIO(text), delimiter=delimiter)
                rows = list(reader)
                if len(rows) > 1 and len(rows[0]) >= 2:
                    header = [c.strip().lower().replace("_", "").replace(" ", "").replace("-", "") for c in rows[0]]
                    roll_idx, name_idx, email_idx = self._find_column_indices(header)
                    if roll_idx is not None and name_idx is not None:
                        records = []
                        for row in rows[1:]:
                            if len(row) > max(roll_idx, name_idx):
                                roll = row[roll_idx].strip()
                                name = row[name_idx].strip()
                                email = row[email_idx].strip() if email_idx is not None and len(row) > email_idx else ""
                                if roll or name:
                                    records.append({"roll_number": roll, "full_name": name, "email": email})
                        if records:
                            return records
            except Exception:
                continue

        # If CSV dialect didn't succeed, extract via regex
        return self._regex_extract_lines(text)

    def _parse_excel(self, content: bytes) -> List[Dict[str, str]]:
        """Parses modern Excel (.xlsx) files using openpyxl."""
        records: List[Dict[str, str]] = []
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                return records

            # Search first 10 rows for a valid header
            header_row_idx = None
            roll_idx, name_idx, email_idx = None, None, None

            for i, r in enumerate(rows[:10]):
                if not r:
                    continue
                header = [str(c or "").strip().lower().replace("_", "").replace(" ", "").replace("-", "") for c in r]
                r_idx, n_idx, e_idx = self._find_column_indices(header)
                if r_idx is not None and n_idx is not None:
                    header_row_idx = i
                    roll_idx, name_idx, email_idx = r_idx, n_idx, e_idx
                    break

            if header_row_idx is not None:
                for row in rows[header_row_idx + 1:]:
                    if not row:
                        continue
                    roll = str(row[roll_idx] or "").strip() if roll_idx < len(row) else ""
                    name = str(row[name_idx] or "").strip() if name_idx < len(row) else ""
                    email = str(row[email_idx] or "").strip() if email_idx is not None and email_idx < len(row) else ""
                    if roll or name:
                        records.append({"roll_number": roll, "full_name": name, "email": email})
            else:
                # Dump cell text and run regex/LLM
                text_lines = []
                for row in rows:
                    text_lines.append(" ".join([str(c) for c in row if c is not None]))
                return self._regex_extract_lines("\n".join(text_lines))
        except Exception as e:
            logger.warning(f"openpyxl failed to parse excel: {e}")
        return records

    def _parse_pdf(self, content: bytes) -> List[Dict[str, str]]:
        """Extracts text from PDF and runs tabular/LLM extraction."""
        text = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        except Exception as e:
            logger.warning(f"pypdf extraction notice: {e}")

        if not text:
            return []
        
        # Try line-by-line regex first
        records = self._regex_extract_lines(text)
        if records:
            return records
        
        # Fallback to Gemini
        return self._extract_with_gemini_text(text)

    def _parse_docx(self, content: bytes) -> List[Dict[str, str]]:
        """Extracts tables and paragraphs from DOCX."""
        records: List[Dict[str, str]] = []
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            # First check tables
            for table in doc.tables:
                if len(table.rows) > 1:
                    header = [c.text.strip().lower().replace("_", "").replace(" ", "").replace("-", "") for c in table.rows[0].cells]
                    roll_idx, name_idx, email_idx = self._find_column_indices(header)
                    if roll_idx is not None and name_idx is not None:
                        for row in table.rows[1:]:
                            cells = row.cells
                            if len(cells) > max(roll_idx, name_idx):
                                roll = cells[roll_idx].text.strip()
                                name = cells[name_idx].text.strip()
                                email = cells[email_idx].text.strip() if email_idx is not None and len(cells) > email_idx else ""
                                if roll or name:
                                    records.append({"roll_number": roll, "full_name": name, "email": email})
                        if records:
                            return records

            # Check paragraph text if no table found
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return self._regex_extract_lines(text)
        except Exception as e:
            logger.warning(f"python-docx extraction notice: {e}")
        return records

    def _parse_zip(self, content: bytes) -> List[Dict[str, str]]:
        """Safely extracts and parses roster files contained within a ZIP archive.
        
        Guards against zip-slip directory traversal vulnerabilities.
        """
        # Import standard zipfile library for archive unpacking
        import zipfile
        # Initialize list to collect extracted records across contained files
        combined_records: List[Dict[str, str]] = []
        # Wrap archive operations in try block to handle corrupted ZIP streams
        try:
            # Open ZIP archive from in-memory byte buffer
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Iterate through all members inside the archive
                for member in zf.infolist():
                    # Defend against zip-slip directory traversal attacks
                    if ".." in member.filename or member.filename.startswith("/") or member.filename.startswith("\\"):
                        # Skip dangerous member paths
                        continue
                    # Skip directory marker entries
                    if member.is_dir():
                        # Continue to next archive item
                        continue
                    # Read member bytes safely from archive
                    member_bytes = zf.read(member.filename)
                    # Recursively parse inner file using multi-format parser
                    inner_records = self.parse_roster_file(member.filename, member_bytes)
                    # Extend combined list with extracted student records
                    combined_records.extend(inner_records)
        # Catch archive read or decompression errors
        except Exception as e:
            # Log warning notice with error details
            logger.warning(f"ZIP roster archive parsing failed: {e}")
        # Return all aggregated student records
        return combined_records

    def _parse_image(self, content: bytes, ext: str) -> List[Dict[str, str]]:
        """Uses Gemini Vision API to OCR and extract student rosters from images."""
        if not self.client:
            logger.warning("Gemini Client not available for image roster parsing")
            return []

        try:
            mime = "image/png" if ext == "png" else "image/jpeg"
            prompt = (
                "You are an expert OCR tool. Analyze this student roster/roll-call image. "
                "Extract all student entries. Return ONLY a valid JSON array of objects with keys: "
                "'roll_number', 'full_name', 'email'. If email is missing, leave it as an empty string. "
                "Do not include any explanation or markdown formatting."
            )
            image_part = types.Part.from_bytes(data=content, mime_type=mime)
            response = self.client.models.generate_content(
                model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
                contents=[image_part, prompt],
            )
            return self._parse_json_records(response.text)
        except Exception as e:
            logger.error(f"Gemini image roster OCR failed: {e}")
            return []

    def _extract_with_gemini_text(self, text: str) -> List[Dict[str, str]]:
        """Sends document text to Gemini to structure student records."""
        if not self.client:
            return []
        try:
            prompt = (
                "Extract all student records from the following roster text. "
                "Return ONLY a valid JSON array with objects containing: "
                "'roll_number', 'full_name', and optional 'email'. "
                "Do not include explanation or markdown code block markers.\n\n"
                f"Text:\n{text[:12000]}"
            )
            response = self.client.models.generate_content(
                model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
                contents=[prompt],
            )
            return self._parse_json_records(response.text)
        except Exception as e:
            logger.error(f"Gemini text roster extraction failed: {e}")
            return []

    def _parse_json_records(self, raw_text: str) -> List[Dict[str, str]]:
        """Safely parses JSON list from model response."""
        if not raw_text:
            return []
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
            if isinstance(data, dict) and "students" in data and isinstance(data["students"], list):
                return data["students"]
        except Exception as e:
            logger.warning(f"Could not parse JSON from model response: {e}")
        return []

    def _find_column_indices(self, header: List[str]):
        """Identifies indices for roll number, name, and email from column headers."""
        roll_idx, name_idx, email_idx = None, None, None
        for idx, col in enumerate(header):
            c = col.strip()
            if c in ("rollnumber", "rollno", "roll", "studentroll", "id", "roll#", "registrationno", "regno", "studentno"):
                roll_idx = idx
            elif c in ("name", "fullname", "studentname", "names", "student"):
                name_idx = idx
            elif c in ("email", "emailaddress", "studentemail", "mail"):
                email_idx = idx
        return roll_idx, name_idx, email_idx

    def _regex_extract_lines(self, text: str) -> List[Dict[str, str]]:
        """Extracts student lines via regex heuristics."""
        records = []
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for line in lines:
            # Pattern 1: e.g. "2024-001, John Doe, john@university.edu" or "2024-001 - John Doe"
            m = re.match(r"^([A-Za-z0-9\-_]{2,20})[\s,;:\t\-]+([A-Za-z\s\.\']{2,40})(?:[\s,;:\t\-]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+))?", line)
            if m:
                roll = m.group(1).strip()
                name = m.group(2).strip()
                email = (m.group(3) or "").strip()
                if not any(header_word in roll.lower() for header_word in ["roll", "name", "id", "number"]):
                    records.append({"roll_number": roll, "full_name": name, "email": email})
        return records

    def _extract_raw_text(self, filename: str, content: bytes, ext: str) -> str:
        """Extracts raw text from bytes."""
        try:
            if ext in {"csv", "tsv", "txt"}:
                return content.decode("utf-8-sig", errors="replace")
            if ext == "pdf":
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                return "\n".join([p.extract_text() or "" for p in reader.pages])
            if ext in {"docx", "doc"}:
                import docx
                doc = docx.Document(io.BytesIO(content))
                return "\n".join([p.text for p in doc.paragraphs])
        except Exception:
            pass
        return ""


roster_parser_service = RosterParserService()

