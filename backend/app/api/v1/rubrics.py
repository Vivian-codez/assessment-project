# Module docstring explaining matrix rubrics API endpoints
"""Matrix Rubrics API endpoints connecting with database and optional cloud sync."""

# Import uuid library to generate unique identifiers for rubrics and criteria
import uuid
import os
import io
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

# Import application settings singleton
from app.core.config import settings
# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import Supabase client singleton for optional cloud sync
from app.core.supabase import supabase
# Import application logger for debugging and operational notices
from app.core.logging import logger
# Import Rubric and RubricCriterion database models
from app.models.rubric import Rubric, RubricCriterion
# Import Course database model
from app.models.course import Course
# Import Classroom database model
from app.models.classroom import Classroom
# Import Pydantic schemas for rubric creation, response serialization, and criteria levels
from app.schemas.rubric import (
    # Schema validating rubric creation payload
    RubricCreate,
    # Schema serializing rubric response payload
    RubricResponse,
    # Schema serializing individual criterion attributes
    RubricCriterionSchema,
    # Schema representing individual tiered scoring levels
    RubricLevel,
    # Schema representing parsed rubric file with descending tiers
    Phase3ParsedRubricResponse,
)
# Import Gemini service singleton for AI rubric parsing
from app.services.gemini_service import gemini_service
# Import authentication dependency resolving the current instructor
from app.api.v1.auth import get_current_instructor
# Import Instructor database model
from app.models.instructor import Instructor

# Initialize FastAPI router instance with /rubrics prefix and Matrix Rubrics tag
router = APIRouter(prefix="/rubrics", tags=["Matrix Rubrics"])


# Helper function formatting a RubricCriterion database model into its schema representation
def _format_criterion(crit: RubricCriterion) -> RubricCriterionSchema:
    # Extract raw levels data or default to empty list
    raw_levels = crit.levels or []
    # Initialize empty list to hold structured RubricLevel objects
    levels = []
    # Check if raw levels is a list
    if isinstance(raw_levels, list):
        # Iterate through each level dictionary
        for lvl in raw_levels:
            # Check if level item is a dictionary
            if isinstance(lvl, dict):
                # Append structured RubricLevel model instance
                levels.append(
                    # Instantiate RubricLevel
                    RubricLevel(
                        # Set tier title
                        level_name=lvl.get("level_name", "Tier"),
                        # Set point value
                        points=float(lvl.get("points", 0.0)),
                        # Set level description
                        description=lvl.get("description", ""),
                    )
                )

    # Resolve criterion title checking criterion_name then name fallback
    crit_name = crit.criterion_name or crit.name or "Criterion"
    # Resolve maximum points checking max_points then max_score fallback
    max_pts = float(crit.max_points if crit.max_points is not None else (crit.max_score or 4.0))

    # Return serialized RubricCriterionSchema instance
    return RubricCriterionSchema(
        # Set criterion ID
        id=crit.id,
        # Set criterion name
        criterion_name=crit_name,
        # Set display name
        name=crit_name,
        # Set description text
        description=crit.description or "",
        # Set weight float defaulting to 25.0%
        weight=float(crit.weight if crit.weight is not None else 25.0),
        # Set max points
        max_points=max_pts,
        # Set max score
        max_score=max_pts,
        # Set ordering index integer
        order_index=int(crit.order_index or 0),
        # Set list of structured levels
        levels=levels,
    )


# Helper function formatting a Rubric database model into its schema representation
def _format_rubric(rubric: Rubric) -> RubricResponse:
    # Resolve rubric title checking title then name fallback
    title = rubric.title or rubric.name or "Untitled Rubric"
    # Resolve total marks checking total_marks then total_max_score fallback
    total_marks = float(rubric.total_marks if rubric.total_marks is not None else (rubric.total_max_score or 100.0))
    # Format each criterion model in rubric criteria relationship
    criteria = [_format_criterion(c) for c in (rubric.criteria or [])]

    # Return serialized RubricResponse instance
    return RubricResponse(
        # Set rubric ID
        id=rubric.id,
        # Set title attribute
        title=title,
        # Set name attribute
        name=title,
        # Set classroom ID
        classroom_id=rubric.classroom_id,
        # Set course ID
        course_id=rubric.course_id or rubric.classroom_id or "",
        # Set total marks
        total_marks=total_marks,
        # Set total max score
        total_max_score=total_marks,
        # Format creation timestamp as ISO string
        created_at=rubric.created_at.isoformat() if rubric.created_at else "",
        # Set formatted criteria list
        criteria=criteria,
    )


# HTTP POST route handler creating a new matrix rubric
@router.post("", response_model=RubricResponse)
def create_rubric(
    # Validate incoming JSON creation payload using RubricCreate schema
    payload: RubricCreate,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing rubric creation
    """Create a new matrix rubric with tiered point descriptions."""
    # Resolve rubric title string and strip whitespace
    title = (payload.title or payload.name or "Untitled Rubric").strip()
    # Resolve target cohort ID checking classroom_id then course_id
    target_id = payload.classroom_id or payload.course_id

    # Compute total marks
    # Extract total marks from payload fields
    total_marks = payload.total_marks or payload.total_max_score or 0.0
    # Check if total marks is zero but criteria were supplied
    if not total_marks and payload.criteria:
        # Initialize running cumulative marks counter
        calc_total = 0.0
        # Iterate over criteria in payload
        for c in payload.criteria:
            # Check if max_points was explicitly specified
            if c.max_points is not None:
                # Add max_points to running total
                calc_total += c.max_points
            # Check if levels were supplied
            elif c.levels:
                # Add highest tier point value to running total
                calc_total += max((float(l.points) for l in c.levels), default=4.0)
            # Check if max_score was specified
            elif c.max_score is not None:
                # Add max_score to running total
                calc_total += c.max_score
            # Fallback default point value
            else:
                # Add default 4 points to running total
                calc_total += 4.0
        # Assign calculated sum to total_marks
        total_marks = calc_total

    # Generate unique UUID string identifier for rubric
    rubric_id = str(uuid.uuid4())

    # Instantiate new Rubric database model
    new_rubric = Rubric(
        # Set rubric ID
        id=rubric_id,
        # Set title
        title=title,
        # Set name
        name=title,
        # Set classroom foreign key
        classroom_id=target_id,
        # Set course foreign key
        course_id=target_id,
        # Set total marks
        total_marks=total_marks,
        # Set total max score
        total_max_score=total_marks,
    )
    # Stage new rubric entity into database session
    db.add(new_rubric)

    # Iterate over criteria payloads with sequence index
    for idx, c in enumerate(payload.criteria or []):
        # Generate unique UUID string for criterion
        crit_id = str(uuid.uuid4())
        # Resolve criterion display name
        crit_name = (c.criterion_name or c.name or f"Criterion {idx + 1}").strip()
        # Serialize levels into dictionary list
        levels_data = [
            # Check for model_dump or dict methods on level object
            lvl.model_dump() if hasattr(lvl, "model_dump") else (lvl.dict() if hasattr(lvl, "dict") else lvl)
            # Iterate through criterion levels
            for lvl in (c.levels or [])
        ]

        # Check if max_points was provided
        if c.max_points is not None:
            # Cast max_points to float
            max_pts = float(c.max_points)
        # Check if levels data was provided
        elif levels_data:
            # Resolve max point value across levels
            max_pts = max((float(l.get("points", 0.0)) for l in levels_data), default=4.0)
        # Check if max_score was provided
        elif c.max_score is not None:
            # Cast max_score to float
            max_pts = float(c.max_score)
        # Fallback default
        else:
            # Assign default 4.0 points
            max_pts = 4.0

        # Instantiate new RubricCriterion database model
        new_crit = RubricCriterion(
            # Set criterion ID
            id=crit_id,
            # Link to parent rubric ID
            rubric_id=rubric_id,
            # Set criterion name
            criterion_name=crit_name,
            # Set display name
            name=crit_name,
            # Set description text
            description=c.description or "",
            # Set weight percentage
            weight=float(c.weight if c.weight is not None else 25.0),
            # Set max points
            max_points=max_pts,
            # Set max score
            max_score=max_pts,
            # Set order index from payload or sequence index
            order_index=c.order_index if c.order_index is not None else idx,
            # Store levels JSON dictionary
            levels=levels_data,
        )
        # Stage criterion entity in database session
        db.add(new_crit)

    # Commit all rubric and criteria entities to PostgreSQL
    db.commit()
    # Refresh rubric instance from database
    db.refresh(new_rubric)

    # Optional cloud sync if enabled
    if settings.USE_SUPABASE:
        # Wrap Supabase sync in try-except block
        try:
            # Upsert rubric record into Supabase rubrics table
            supabase.table("rubrics").upsert({
                # Set rubric ID
                "id": rubric_id,
                # Set title
                "title": title,
                # Set name
                "name": title,
                # Set classroom ID
                "classroom_id": target_id,
                # Set course ID
                "course_id": target_id,
                # Set total marks
                "total_marks": total_marks,
                # Set total max score
                "total_max_score": total_marks,
            }).execute()
            # Iterate through each created criterion model
            for crit in new_rubric.criteria:
                # Upsert criterion record into Supabase rubric_criteria table
                supabase.table("rubric_criteria").upsert({
                    # Set criterion ID
                    "id": crit.id,
                    # Set parent rubric ID
                    "rubric_id": rubric_id,
                    # Set criterion name
                    "criterion_name": crit.criterion_name,
                    # Set display name
                    "name": crit.name,
                    # Set description
                    "description": crit.description,
                    # Set max points
                    "max_points": crit.max_points,
                    # Set max score
                    "max_score": crit.max_score,
                    # Set sequence order index
                    "order_index": crit.order_index,
                    # Set levels JSON
                    "levels": crit.levels,
                }).execute()
        # Catch synchronization errors
        except Exception as e:
            # Log warning message on cloud sync notice
            logger.warning(f"Cloud rubric sync notice: {e}")

    # Return formatted RubricResponse schema instance
    return _format_rubric(new_rubric)


# Helper function to extract text from an uploaded file content of any format
def extract_text_from_file_content(content: bytes, filename: str) -> str:
    # Docstring explaining multi-format text extraction for rubrics
    """Extracts raw text from any uploaded rubric file format (PDF, DOCX, XLSX, TXT, CSV, Markdown)."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext in ["txt", "csv", "md"]:
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    elif ext == "docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception:
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    return "".join(tree.itertext())
            except Exception:
                return f"Uploaded DOCX Rubric: {filename}"
    elif ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join([p.extract_text() or "" for p in reader.pages if p.extract_text()])
        except Exception:
            return f"Uploaded PDF Rubric: {filename}"
    elif ext in ["xlsx", "xls"]:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                shared = []
                if "xl/sharedStrings.xml" in z.namelist():
                    tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                    shared = [elem.text for elem in tree.iter() if elem.text]
                return " ".join(shared) if shared else f"Spreadsheet Rubric: {filename}"
        except Exception:
            return f"Spreadsheet Rubric: {filename}"
    return f"Uploaded Rubric Asset: {filename} ({len(content)} bytes)"


# HTTP POST route handler parsing any rubric file into structured criteria for teacher review
@router.post("/parse-rubric-file", response_model=Phase3ParsedRubricResponse)
async def parse_rubric_file(
    file: UploadFile = File(...),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Universal rubric file parser: accepts PDF, DOCX, XLSX, TXT, CSV, or images and uses Gemini to parse into matrix criteria with descending points."""
    content = await file.read()
    filename = file.filename or "rubric_document"
    extracted_text = extract_text_from_file_content(content, filename)
    return gemini_service.parse_rubric_document(extracted_text, filename)


# HTTP POST route handler uploading a rubric file (PDF, DOCX, XLSX, TXT, CSV, images)
@router.post("/upload", response_model=RubricResponse)
async def upload_rubric_file(
    file: UploadFile = File(...),
    classroom_id: Optional[str] = Form(None),
    course_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Upload any rubric document (PDF, DOCX, XLSX, TXT, CSV, images) with text extraction and automatic criteria configuration."""
    target_id = classroom_id or course_id
    filename = file.filename or "rubric_document"
    base_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip().title()
    rubric_title = (title or base_name or "Uploaded Matrix Rubric").strip()
    content = await file.read()
    extracted_text = extract_text_from_file_content(content, filename)

    # Use Gemini rubric parser to parse criteria from file content
    parsed_rubric = gemini_service.parse_rubric_document(extracted_text, filename)

    total_marks = parsed_rubric.total_marks or 100.0
    rubric_id = str(uuid.uuid4())

    new_rubric = Rubric(
        id=rubric_id,
        title=rubric_title or parsed_rubric.title,
        name=rubric_title or parsed_rubric.title,
        classroom_id=target_id,
        course_id=target_id,
        total_marks=total_marks,
        total_max_score=total_marks,
    )
    db.add(new_rubric)

    for idx, c_def in enumerate(parsed_rubric.criteria):
        crit_id = str(uuid.uuid4())
        levels_data = [
            {"level_name": lvl.level_name, "points": lvl.points, "description": lvl.description}
            for lvl in c_def.levels
        ]
        new_crit = RubricCriterion(
            id=crit_id,
            rubric_id=rubric_id,
            criterion_name=c_def.criterion_name or f"Criterion {idx+1}",
            name=c_def.criterion_name or f"Criterion {idx+1}",
            description=c_def.description or "",
            weight=c_def.weight if c_def.weight is not None else (100.0 / len(parsed_rubric.criteria)),
            max_points=max((l["points"] for l in levels_data), default=4.0),
            max_score=max((l["points"] for l in levels_data), default=4.0),
            order_index=idx,
            levels=levels_data,
        )
        db.add(new_crit)

    db.commit()
    db.refresh(new_rubric)
    return _format_rubric(new_rubric)

    return _format_rubric(new_rubric)


# HTTP GET route handler returning list of rubrics with optional cohort filtering
@router.get("", response_model=List[RubricResponse])
def list_rubrics(
    # Optional classroom ID filter query parameter
    classroom_id: Optional[str] = Query(None),
    # Optional course ID filter query parameter
    course_id: Optional[str] = Query(None),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing rubric list retrieval
    """Retrieve all rubrics, optionally filtered by classroom or course ID."""
    # Resolve target cohort ID from classroom_id or course_id
    target_id = classroom_id or course_id
    # Construct base query targeting Rubric database model
    query = db.query(Rubric)
    # Check if target cohort filter was supplied
    if target_id:
        # Filter rubrics matching classroom_id or course_id
        query = query.filter(
            # Match classroom or course foreign keys
            (Rubric.classroom_id == target_id) | (Rubric.course_id == target_id)
        )
    # Execute query ordering records by creation timestamp descending
    rubrics = query.order_by(Rubric.created_at.desc()).all()

    # Optional cloud sync fallback if local DB has none and cloud active
    if not rubrics and settings.USE_SUPABASE:
        # Wrap Supabase query in try block
        try:
            # Initialize select query on Supabase rubrics table
            q = supabase.table("rubrics").select("*")
            # Apply cohort filter if provided
            if target_id:
                # Add or filter on classroom_id and course_id
                q = q.or_(f"classroom_id.eq.{target_id},course_id.eq.{target_id}")
            # Execute query ordering by created_at descending
            res = q.order("created_at", desc=True).execute()
            # Iterate through fetched rubric records
            for r_row in (res.data or []):
                # Instantiate new Rubric model from cloud record
                new_r = Rubric(
                    # Set rubric ID
                    id=str(r_row["id"]),
                    # Set title
                    title=r_row.get("title") or r_row.get("name"),
                    # Set name
                    name=r_row.get("name") or r_row.get("title"),
                    # Set classroom ID
                    classroom_id=r_row.get("classroom_id"),
                    # Set course ID
                    course_id=r_row.get("course_id"),
                    # Set total marks float
                    total_marks=float(r_row.get("total_marks") or r_row.get("total_max_score") or 0.0),
                    # Set total max score float
                    total_max_score=float(r_row.get("total_max_score") or r_row.get("total_marks") or 100.0),
                )
                # Stage rubric entity in database session
                db.add(new_r)
                # Append to local list
                rubrics.append(new_r)
            # Commit synchronized rubrics to local PostgreSQL database
            db.commit()
        # Catch query errors
        except Exception as e:
            # Log debug notification regarding cloud sync fallback
            logger.debug(f"Cloud rubric sync fallback notice: {e}")

    # Return list of formatted RubricResponse schema representations
    return [_format_rubric(r) for r in rubrics]


# HTTP GET route handler returning specific rubric by ID
@router.get("/{rubric_id}", response_model=RubricResponse)
def get_rubric(
    # Rubric ID string extracted from URL path parameter
    rubric_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing rubric detail retrieval
    """Retrieve a matrix rubric and all its criteria with level descriptions."""
    # Query database for Rubric matching rubric_id
    r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    # Check if rubric was not found
    if not r:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Rubric not found")
    # Return formatted RubricResponse schema
    return _format_rubric(r)


# HTTP GET route handler returning rubrics for a specific course (compatibility route)
@router.get("/courses/{course_id}/rubrics", response_model=List[RubricResponse])
def get_course_rubrics(
    # Course ID string extracted from URL path parameter
    course_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing course rubrics alias
    """Retrieve all rubrics for a given course or classroom (backward compatibility)."""
    # Delegate to list_rubrics handler with course ID
    return list_rubrics(classroom_id=course_id, course_id=course_id, db=db, current_instructor=current_instructor)


# HTTP DELETE route handler deleting a rubric and cascading criteria
@router.delete("/{rubric_id}", status_code=204)
def delete_rubric(
    rubric_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete a rubric and cleanly decouple associated assignments and criteria."""
    # Query database for target Rubric
    r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rubric not found")

    # Validate ownership if linked to a classroom or course
    if r.classroom_id:
        from app.models.classroom import Classroom
        cl = db.query(Classroom).filter(Classroom.id == r.classroom_id).first()
        if cl and cl.instructor_id and current_instructor and current_instructor.id and cl.instructor_id != current_instructor.id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this rubric.")
    elif r.course_id:
        from app.models.course import Course
        crs = db.query(Course).filter(Course.id == r.course_id).first()
        if crs and crs.instructor_id and current_instructor and current_instructor.id and crs.instructor_id != current_instructor.id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this rubric.")

    # Cleanly detach any assignments referencing this rubric to prevent foreign key errors
    from app.models.assignment import Assignment
    linked_assignments = db.query(Assignment).filter(Assignment.rubric_id == rubric_id).all()
    for assign in linked_assignments:
        assign.rubric_id = None

    # Delete rubric entity from database session (cascades to criteria)
    db.delete(r)
    db.commit()

    # Check if cloud Supabase synchronization is active
    if settings.USE_SUPABASE:
        try:
            supabase.table("rubric_criteria").delete().eq("rubric_id", rubric_id).execute()
            supabase.table("rubrics").delete().eq("id", rubric_id).execute()
        except Exception as e:
            logger.warning(f"Cloud rubric delete notice: {e}")

    return None
