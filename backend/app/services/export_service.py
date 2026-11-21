# Module docstring explaining Export Service for CSV and Excel Gradebook generation
"""Export Service generating RFC-4180 CSVs with UTF-8 BOM, formula injection defense, and XLSX workbooks."""

# Import standard library modules for CSV formatting, in-memory IO, regular expressions, and cryptography
import csv
import io
import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# Import application logger for export operation telemetry
from app.core.logging import logger
# Import ORM models for courses, assignments, submissions, students, rubrics
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.student import Student


def extract_roll_number(filename: str, custom_regex: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Extract student institutional roll number from an uploaded submission filename using regex patterns.

    Args:
        filename (str): Original uploaded file name (e.g., 'S102_lab1_submission.py').
        custom_regex (Optional[str]): Educator-specified regular expression pattern with capture group.

    Returns:
        Tuple[Optional[str], str]: Tuple containing (extracted_roll_number, match_status).
            match_status is one of: 'matched', 'no_roll_number_found', 'multiple_rolls'.
    """
    # Check if filename is empty or invalid
    if not filename:
        # Return none and not found status
        return None, "no_roll_number_found"

    # Normalize filename removing path separators
    clean_name = filename.replace("\\", "/").split("/")[-1]

    # If educator provided a custom regex, attempt match first
    if custom_regex:
        # Wrap custom regex compilation in try-except block
        try:
            # Search for custom pattern match
            match = re.search(custom_regex, clean_name, re.IGNORECASE)
            # Check if match was found with capture group
            if match and match.groups():
                # Return captured roll number
                return match.group(1).strip(), "matched"
        # Catch regex compilation or execution errors
        except Exception as exc:
            # Log regex evaluation warning
            logger.warning(f"[ROLL-EXTRACT] Custom regex error for '{clean_name}': {exc}")

    # Standard regular expression candidate patterns in order of priority
    patterns = [
        # Explicit roll/id prefix preceded by start or delimiter (e.g., roll-S102, id_202401, std_A104)
        r"(?:^|[-_])(?:roll|id|reg|std)[-_]?([a-zA-Z0-9]+)",
        # Leading alphanumeric identifier containing at least one digit followed by separator (e.g., S102_assignment1.py, CS401-02-main.cpp, 2024047_lab.pdf)
        r"^([a-zA-Z0-9]*\d[a-zA-Z0-9]*)[-_]",
        # Standard alphanumeric academic roll code containing digits (e.g., CS101, S102, 21BCSE042)
        r"([a-zA-Z]{1,4}[0-9]{2,8})",
    ]

    # Iterate through prioritized regex patterns in order
    for pat in patterns:
        # Search for pattern matches in clean filename
        matches = re.findall(pat, clean_name, re.IGNORECASE)
        # Collect distinct candidates found by this pattern
        candidates: List[str] = []
        for m in matches:
            tok = (m if isinstance(m, str) else m[0]).strip()
            if tok and tok.upper() not in [c.upper() for c in candidates]:
                candidates.append(tok)
        # If this pattern found matches, return result immediately according to priority
        if len(candidates) == 1:
            return candidates[0], "matched"
        elif len(candidates) > 1:
            return candidates[0], "multiple_rolls"

    # If no pattern matched any candidate roll number
    return None, "no_roll_number_found"


def match_roll_to_roster(extracted_roll: Optional[str], enrolled_students: List[Student]) -> Tuple[Optional[Student], str]:
    """Map an extracted roll number string to an enrolled student record in the classroom roster.

    Args:
        extracted_roll (Optional[str]): Alphanumeric roll number string.
        enrolled_students (List[Student]): List of enrolled students in the target cohort.

    Returns:
        Tuple[Optional[Student], str]: Tuple of (matched_student, status).
            status is one of: 'matched', 'no_roll_number_found', 'roll_number_not_in_roll_call'.
    """
    # If no roll number was extracted, return not found status
    if not extracted_roll:
        return None, "no_roll_number_found"

    # Normalize extracted roll string for case-insensitive comparison
    norm_roll = extracted_roll.strip().lower()

    # Iterate through enrolled students in roster
    for std in enrolled_students:
        # Check if student's roll number matches normalized target
        if std.roll_number and std.roll_number.strip().lower() == norm_roll:
            # Return matched student and matched status
            return std, "matched"

    # If no enrolled student matched the roll number
    return None, "roll_number_not_in_roll_call"


def sanitize_csv_cell(value: Any) -> str:
    """Sanitize string values to defend against CSV Formula Injection (CWE-1236).

    Prepends a single apostrophe (') to any cell beginning with dangerous execution characters
    (=, +, -, @, \\t, \\r) so spreadsheet applications (Excel, LibreOffice, Google Sheets)
    treat the cell strictly as plain text rather than executing dynamic formula code.

    Args:
        value (Any): Cell value to sanitize.

    Returns:
        str: Sanitized cell text safe for spreadsheet export.
    """
    # If value is None, return empty string
    if value is None:
        return ""

    # Convert value to string and strip surrounding whitespace
    s_val = str(value).strip()

    # If string is empty, return empty string
    if not s_val:
        return ""

    # Dangerous formula execution prefix characters
    formula_triggers = ("=", "+", "-", "@", "\t", "\r")

    # Check if cell begins with any formula trigger character
    if s_val.startswith(formula_triggers):
        # Prepend single quote apostrophe to force text interpretation
        return f"'{s_val}"

    # Return safe sanitized string
    return s_val


def generate_gradebook_csv(
    course: Course,
    assignment: Optional[Assignment],
    submissions: List[Submission],
    enrolled_students: List[Student],
    mode: str = "final",
    format_type: str = "default",
) -> Tuple[str, str]:
    """Generate a RFC-4180 compliant CSV gradebook with UTF-8 BOM and formula injection protection.

    Guarantees that EVERY enrolled student in the roster is represented in the export.
    Calculates exact arithmetic marks using pure-Python floating point math rounded to 2 decimals.

    Args:
        course (Course): Parent course entity.
        assignment (Optional[Assignment]): Target assignment if filtered, or None for course aggregate.
        submissions (List[Submission]): Evaluated student submissions list.
        enrolled_students (List[Student]): Complete roster of enrolled students.
        mode (str): Export mode - 'final' (approved grades only) or 'draft' (includes AI suggestions).
        format_type (str): Output layout - 'default', 'google_classroom', or 'moodle'.

    Returns:
        Tuple[str, str]: Tuple containing (csv_text_with_bom, sha256_checksum).
    """
    # Create in-memory StringIO buffer for CSV generation
    output = io.StringIO()

    # Prepend UTF-8 Byte Order Mark (BOM) so Excel opens UTF-8 text with correct accent encoding
    output.write("\ufeff")

    # Initialize CSV writer with standard RFC-4180 quoting rules
    writer = csv.writer(output, dialect="excel", quoting=csv.QUOTE_MINIMAL)

    # Map submissions by student roll number (normalized lowercase)
    submission_map: Dict[str, Submission] = {}
    # Iterate through provided submissions
    for sub in submissions:
        # Resolve roll number key
        roll_key = (sub.student_roll or sub.student_identifier or "").strip().lower()
        if roll_key:
            submission_map[roll_key] = sub

    # Resolve list of criteria columns if an assignment with rubric exists
    criteria_names: List[str] = []
    # Check if assignment and rubric are available
    if assignment and assignment.rubric and assignment.rubric.criteria:
        # Collect criteria names in defined order
        criteria_names = [c.name for c in assignment.rubric.criteria]

    # --- FORMAT 1: GOOGLE CLASSROOM CSV FORMAT ---
    if format_type == "google_classroom":
        # Google Classroom standard header row
        writer.writerow(["Student Name", "Email Address", "Assignment Name", "Grade"])
        # Assignment display title
        assign_title = assignment.title if assignment else "Overall Gradebook"
        # Iterate through every student in enrolled roster
        for std in sorted(enrolled_students, key=lambda s: s.full_name or ""):
            # Lookup submission for this student
            roll_key = (std.roll_number or "").strip().lower()
            sub = submission_map.get(roll_key)

            # Determine grade score
            grade_str = ""
            if sub and sub.draft_grade:
                # Check mode: final requires approved status
                if mode == "final":
                    if sub.status == "approved" and sub.draft_grade.final_score is not None:
                        grade_str = f"{sub.draft_grade.final_score:.2f}"
                else:
                    # Draft mode includes suggested score
                    score = sub.draft_grade.final_score if sub.draft_grade.final_score is not None else (sub.draft_grade.suggested_score or 0.0)
                    grade_str = f"{score:.2f}"

            # Write sanitized student row
            writer.writerow([
                sanitize_csv_cell(std.full_name),
                sanitize_csv_cell(std.email or ""),
                sanitize_csv_cell(assign_title),
                sanitize_csv_cell(grade_str),
            ])

    # --- FORMAT 2: MOODLE GRADEBOOK CSV FORMAT ---
    elif format_type == "moodle":
        # Moodle standard header row
        writer.writerow([
            "Identifier",
            "Full name",
            "ID number",
            "Email address",
            "Status",
            "Grade",
            "Maximum Grade",
            "Feedback comments",
        ])
        # Maximum possible grade for assignment
        max_marks_val = f"{assignment.max_score:.2f}" if (assignment and assignment.max_score) else "100.00"

        # Iterate through enrolled students
        for std in sorted(enrolled_students, key=lambda s: s.roll_number or ""):
            roll_key = (std.roll_number or "").strip().lower()
            sub = submission_map.get(roll_key)

            status_str = "Not submitted"
            grade_str = ""
            feedback_str = ""

            if sub:
                status_str = sub.status.capitalize()
                if sub.draft_grade:
                    feedback_str = sub.draft_grade.feedback or ""
                    if mode == "final":
                        if sub.status == "approved" and sub.draft_grade.final_score is not None:
                            grade_str = f"{sub.draft_grade.final_score:.2f}"
                    else:
                        score = sub.draft_grade.final_score if sub.draft_grade.final_score is not None else (sub.draft_grade.suggested_score or 0.0)
                        grade_str = f"{score:.2f}"

            writer.writerow([
                sanitize_csv_cell(std.id),
                sanitize_csv_cell(std.full_name),
                sanitize_csv_cell(std.roll_number),
                sanitize_csv_cell(std.email or ""),
                sanitize_csv_cell(status_str),
                sanitize_csv_cell(grade_str),
                sanitize_csv_cell(max_marks_val),
                sanitize_csv_cell(feedback_str),
            ])

    # --- FORMAT 3: VERISM DEFAULT DETAILED GRADEBOOK CSV ---
    else:
        # Build comprehensive default CSV header row
        header = [
            "Roll Number",
            "Student Name",
            "Email",
            "Assignment",
            "Total Marks",
            "Max Marks",
            "Percentage",
        ]
        # Append per-criterion columns
        for c_name in criteria_names:
            header.append(f"Criterion: {c_name}")
        # Append status and integrity columns
        header.extend([
            "Status",
            "Similarity Risk",
            "AI Writing Indicator",
            "Feedback Summary",
            "Graded At",
        ])
        # Write sanitized header
        writer.writerow([sanitize_csv_cell(h) for h in header])

        # Maximum possible marks
        max_marks = assignment.max_score if (assignment and assignment.max_score) else 100.0
        assign_name = assignment.title if assignment else course.name

        # Iterate through every enrolled student in course roster
        for std in sorted(enrolled_students, key=lambda s: s.roll_number or ""):
            roll_key = (std.roll_number or "").strip().lower()
            sub = submission_map.get(roll_key)

            # Case A: Student has NOT submitted
            if not sub:
                row = [
                    sanitize_csv_cell(std.roll_number),
                    sanitize_csv_cell(std.full_name),
                    sanitize_csv_cell(std.email or ""),
                    sanitize_csv_cell(assign_name),
                    sanitize_csv_cell("0.00"),
                    sanitize_csv_cell(f"{max_marks:.2f}"),
                    sanitize_csv_cell("0.00%"),
                ]
                # Empty values for each criterion
                for _ in criteria_names:
                    row.append(sanitize_csv_cell("0.00"))
                # Status and indicators
                row.extend([
                    sanitize_csv_cell("Missing"),
                    sanitize_csv_cell("N/A"),
                    sanitize_csv_cell("N/A"),
                    sanitize_csv_cell("No submission recorded"),
                    sanitize_csv_cell("N/A"),
                ])
                writer.writerow(row)
                continue

            # Case B: Student has submitted work
            draft = sub.draft_grade
            # Resolve awarded score based on mode
            if mode == "final":
                # Final mode only displays approved grades
                if sub.status == "approved" and draft and draft.final_score is not None:
                    total_score = draft.final_score
                    status_text = "Approved"
                else:
                    total_score = 0.0
                    status_text = "Pending Approval"
            else:
                # Draft mode displays suggested or final score
                total_score = (draft.final_score if draft and draft.final_score is not None else (draft.suggested_score if draft else 0.0))
                status_text = sub.status.capitalize()

            # Pure-Python arithmetic: clamp score between 0 and max_marks
            total_score = max(0.0, min(float(max_marks), float(total_score)))
            # Compute percentage
            pct_val = (total_score / max_marks) * 100.0 if max_marks > 0 else 0.0

            # Construct row start
            row = [
                sanitize_csv_cell(std.roll_number),
                sanitize_csv_cell(std.full_name),
                sanitize_csv_cell(std.email or ""),
                sanitize_csv_cell(assign_name),
                sanitize_csv_cell(f"{total_score:.2f}"),
                sanitize_csv_cell(f"{max_marks:.2f}"),
                sanitize_csv_cell(f"{pct_val:.2f}%"),
            ]

            # Parse criteria breakdown JSON if available
            crit_dict: Dict[str, float] = {}
            if draft and draft.criteria_breakdown:
                for c_entry in draft.criteria_breakdown:
                    c_k = c_entry.get("criterion_name") or c_entry.get("name") or ""
                    c_pts = float(c_entry.get("points_awarded") or c_entry.get("score") or 0.0)
                    if c_k:
                        crit_dict[c_k.strip().lower()] = c_pts

            # Append criteria scores in exact header order
            for c_name in criteria_names:
                pts = crit_dict.get(c_name.strip().lower(), 0.0)
                row.append(sanitize_csv_cell(f"{pts:.2f}"))

            # Determine similarity risk label
            sim_score = sub.similarity_score or 0.0
            if sim_score >= 90.0:
                sim_label = f"Critical ({sim_score:.0f}%)"
            elif sim_score >= 70.0:
                sim_label = f"High ({sim_score:.0f}%)"
            elif sim_score >= 40.0:
                sim_label = f"Moderate ({sim_score:.0f}%)"
            else:
                sim_label = f"Low ({sim_score:.0f}%)"

            # Determine AI indicator label
            ai_score = sub.ai_content_probability or 0.0
            ai_label = f"{ai_score:.0f}%" if ai_score >= 65.0 else "Normal"

            # Format graded timestamp
            graded_date_str = sub.updated_at.strftime("%Y-%m-%d %H:%M UTC") if sub.updated_at else "N/A"

            # Append trailing status columns
            row.extend([
                sanitize_csv_cell(status_text),
                sanitize_csv_cell(sim_label),
                sanitize_csv_cell(ai_label),
                sanitize_csv_cell(draft.feedback if draft else ""),
                sanitize_csv_cell(graded_date_str),
            ])

            # Write data row to CSV buffer
            writer.writerow(row)

    # Retrieve entire CSV text from buffer
    csv_content = output.getvalue()

    # Calculate SHA-256 cryptographic checksum of generated byte content for audit logs
    sha256_hash = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()

    # Return CSV text with BOM and computed checksum
    return csv_content, sha256_hash


def generate_gradebook_xlsx(
    course: Course,
    assignment: Optional[Assignment],
    submissions: List[Submission],
    enrolled_students: List[Student],
    mode: str = "final",
) -> Tuple[bytes, str]:
    """Generate a styled Excel (.xlsx) gradebook workbook with colors, bold headers, and number formatting.

    Args:
        course (Course): Parent course entity.
        assignment (Optional[Assignment]): Target assignment if filtered, or None.
        submissions (List[Submission]): Student submissions list.
        enrolled_students (List[Student]): Roster of all enrolled students.
        mode (str): Export mode ('final' or 'draft').

    Returns:
        Tuple[bytes, str]: Tuple containing (xlsx_bytes, sha256_checksum).
    """
    # Import openpyxl library components
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # Create new Excel workbook
    wb = openpyxl.Workbook()
    # Select active worksheet
    ws = wb.active
    # Set worksheet tab title
    ws.title = "Gradebook"

    # Define Verism AI styling tokens
    header_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")  # Teal brand color
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_side = Side(border_style="thin", color="E2E8F0")
    thin_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    # Map submissions by student roll number
    sub_map: Dict[str, Submission] = {}
    for sub in submissions:
        r_k = (sub.student_roll or sub.student_identifier or "").strip().lower()
        if r_k:
            sub_map[r_k] = sub

    # Collect criteria names
    criteria_names: List[str] = []
    if assignment and assignment.rubric and assignment.rubric.criteria:
        criteria_names = [c.name for c in assignment.rubric.criteria]

    # Assemble headers
    headers = ["Roll Number", "Student Name", "Email", "Assignment", "Total Marks", "Max Marks", "Percentage"]
    for c_name in criteria_names:
        headers.append(c_name)
    headers.extend(["Status", "Similarity Risk", "AI Indicator", "Feedback", "Graded At"])

    # Write header row
    ws.append(headers)

    # Style header row (Row 1)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    max_marks = assignment.max_score if (assignment and assignment.max_score) else 100.0
    assign_name = assignment.title if assignment else course.name

    # Write data rows for all enrolled students
    current_row = 2
    for std in sorted(enrolled_students, key=lambda s: s.roll_number or ""):
        r_k = (std.roll_number or "").strip().lower()
        sub = sub_map.get(r_k)

        if not sub:
            # Missing student row
            row_data = [
                std.roll_number,
                std.full_name,
                std.email or "",
                assign_name,
                0.0,
                max_marks,
                0.0,
            ]
            for _ in criteria_names:
                row_data.append(0.0)
            row_data.extend(["Missing", "N/A", "N/A", "No submission recorded", "N/A"])
        else:
            draft = sub.draft_grade
            if mode == "final":
                if sub.status == "approved" and draft and draft.final_score is not None:
                    score_val = draft.final_score
                    status_str = "Approved"
                else:
                    score_val = 0.0
                    status_str = "Pending Approval"
            else:
                score_val = draft.final_score if (draft and draft.final_score is not None) else (draft.suggested_score if draft else 0.0)
                status_str = sub.status.capitalize()

            score_val = max(0.0, min(float(max_marks), float(score_val)))
            pct_val = (score_val / max_marks) if max_marks > 0 else 0.0

            row_data = [
                std.roll_number,
                std.full_name,
                std.email or "",
                assign_name,
                score_val,
                max_marks,
                pct_val,
            ]

            crit_dict: Dict[str, float] = {}
            if draft and draft.criteria_breakdown:
                for c_entry in draft.criteria_breakdown:
                    c_k = c_entry.get("criterion_name") or c_entry.get("name") or ""
                    c_pts = float(c_entry.get("points_awarded") or c_entry.get("score") or 0.0)
                    if c_k:
                        crit_dict[c_k.strip().lower()] = c_pts

            for c_name in criteria_names:
                row_data.append(crit_dict.get(c_name.strip().lower(), 0.0))

            sim_val = sub.similarity_score or 0.0
            sim_str = f"{sim_val:.0f}%" if sim_val >= 40.0 else "Low (<40%)"
            ai_val = sub.ai_content_probability or 0.0
            ai_str = f"{ai_val:.0f}%" if ai_val >= 65.0 else "Normal"
            graded_str = sub.updated_at.strftime("%Y-%m-%d %H:%M UTC") if sub.updated_at else "N/A"

            row_data.extend([
                status_str,
                sim_str,
                ai_str,
                draft.feedback if draft else "",
                graded_str,
            ])

        ws.append(row_data)

        # Style data cells
        for c_idx in range(1, len(row_data) + 1):
            c_cell = ws.cell(row=current_row, column=c_idx)
            c_cell.font = data_font
            c_cell.border = thin_border
            # Numeric column formatting
            if c_idx in (5, 6):
                c_cell.number_format = "#,##0.00"
                c_cell.alignment = right_align
            elif c_idx == 7:
                c_cell.number_format = "0.0%"
                c_cell.alignment = right_align
            elif 7 < c_idx <= 7 + len(criteria_names):
                c_cell.number_format = "#,##0.00"
                c_cell.alignment = right_align
            elif c_idx in (1, 8 + len(criteria_names), 9 + len(criteria_names), 10 + len(criteria_names)):
                c_cell.alignment = center_align
            else:
                c_cell.alignment = left_align

        current_row += 1

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save workbook to in-memory bytes buffer
    stream = io.BytesIO()
    wb.save(stream)
    xlsx_bytes = stream.getvalue()

    # Calculate SHA-256 hash
    sha256_hash = hashlib.sha256(xlsx_bytes).hexdigest()

    return xlsx_bytes, sha256_hash
