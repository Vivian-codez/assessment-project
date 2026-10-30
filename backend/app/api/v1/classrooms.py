"""Classroom Roster & Roll Call Management API endpoints (Local-first with optional cloud sync)."""

import csv
import io
import uuid
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.supabase import supabase
from app.core.logging import logger
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.course import Course
from app.schemas.classroom import (
    StudentItem,
    StudentResponse,
    StudentUploadCSVResponse,
    ClassroomCreate,
    ClassroomResponse,
)
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(prefix="/classrooms", tags=["Classrooms & Roll Call"])


@router.get("", response_model=List[ClassroomResponse])
def get_classrooms(
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all classrooms for the active instructor with live student counts."""
    # Ensure any existing Course records have corresponding Classroom entries
    courses = db.query(Course).all()
    for crs in courses:
        existing_cl = db.query(Classroom).filter(Classroom.id == crs.id).first()
        if not existing_cl:
            new_cl = Classroom(
                id=crs.id,
                name=crs.name,
                code=crs.code,
                instructor_id=crs.instructor_id,
                created_at=crs.created_at,
            )
            db.add(new_cl)
    db.commit()

    # Query all classrooms
    query = db.query(Classroom)
    if current_instructor and current_instructor.id:
        # Show all instructor classrooms or general
        inst_cls = query.filter((Classroom.instructor_id == current_instructor.id) | (Classroom.instructor_id == None)).order_by(Classroom.created_at.desc()).all()
        classrooms = inst_cls if inst_cls else query.order_by(Classroom.created_at.desc()).all()
    else:
        classrooms = query.order_by(Classroom.created_at.desc()).all()

    # Optional cloud sync if enabled
    if settings.USE_SUPABASE:
        try:
            res = supabase.table("classrooms").select("*").execute()
            for row in (res.data or []):
                r_id = str(row["id"])
                if not any(c.id == r_id for c in classrooms):
                    new_c = Classroom(
                        id=r_id,
                        name=row["name"],
                        code=row["code"],
                        instructor_id=row.get("instructor_id"),
                    )
                    db.add(new_c)
                    classrooms.append(new_c)
            db.commit()
        except Exception as e:
            logger.debug(f"Cloud classroom sync notice: {e}")

    results = []
    for c in classrooms:
        st_count = db.query(Student).filter(Student.classroom_id == c.id).count()
        results.append(
            ClassroomResponse(
                id=c.id,
                name=c.name,
                code=c.code,
                instructor_id=str(c.instructor_id or ""),
                students_count=st_count,
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
        )
    return results


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Create a new classroom / course for enrollment."""
    c_id = str(uuid.uuid4())
    inst_id = current_instructor.id if current_instructor else None

    # Persist Classroom to local database
    new_classroom = Classroom(
        id=c_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        instructor_id=inst_id,
    )
    db.add(new_classroom)

    # Also keep Course table synchronized for unified assignment workflows
    new_course = Course(
        id=c_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        section="A",
        tone="lav",
        students_count=0,
        instructor_id=inst_id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_classroom)

    # Optional cloud sync if enabled
    if settings.USE_SUPABASE:
        try:
            supabase.table("classrooms").upsert({
                "id": c_id,
                "name": payload.name.strip(),
                "code": payload.code.strip(),
                "instructor_id": inst_id,
            }).execute()
            supabase.table("courses").upsert({
                "id": c_id,
                "name": payload.name.strip(),
                "code": payload.code.strip(),
                "section": "A",
                "tone": "lav",
                "students_count": 0,
                "instructor_id": inst_id,
            }).execute()
        except Exception as e:
            logger.warning(f"Cloud classroom sync notice: {e}")

    return ClassroomResponse(
        id=new_classroom.id,
        name=new_classroom.name,
        code=new_classroom.code,
        instructor_id=str(new_classroom.instructor_id or ""),
        students_count=0,
        created_at=new_classroom.created_at.isoformat() if new_classroom.created_at else "",
    )


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(
    classroom_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve details for a single classroom."""
    c = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not c:
        # Check if matching course exists
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        if crs:
            c = Classroom(
                id=crs.id,
                name=crs.name,
                code=crs.code,
                instructor_id=crs.instructor_id,
                created_at=crs.created_at,
            )
            db.add(c)
            db.commit()
            db.refresh(c)

    if not c:
        raise HTTPException(status_code=404, detail="Classroom not found")

    st_count = db.query(Student).filter(Student.classroom_id == c.id).count()
    return ClassroomResponse(
        id=c.id,
        name=c.name,
        code=c.code,
        instructor_id=str(c.instructor_id or ""),
        students_count=st_count,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete a classroom and cascade delete all its students and rubrics."""
    c = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if c:
        db.delete(c)
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    if crs:
        db.delete(crs)
    db.commit()

    if settings.USE_SUPABASE:
        try:
            supabase.table("students").delete().eq("classroom_id", classroom_id).execute()
            supabase.table("rubrics").delete().eq("classroom_id", classroom_id).execute()
            supabase.table("classrooms").delete().eq("id", classroom_id).execute()
        except Exception as e:
            logger.warning(f"Cloud classroom delete notice: {e}")

    return None


# ==============================================================================
# Student Roll Call Management
# ==============================================================================

@router.post("/{classroom_id}/students/manual")
def enroll_students_manual(
    classroom_id: str,
    payload: Union[List[StudentItem], Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Batch enroll students into a classroom either one-by-one or multi-line."""
    # Ensure classroom exists (or create from course)
    cl = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not cl:
        crs = db.query(Course).filter(Course.id == classroom_id).first()
        if crs:
            cl = Classroom(id=crs.id, name=crs.name, code=crs.code, instructor_id=crs.instructor_id)
            db.add(cl)
            db.commit()
            db.refresh(cl)
        else:
            raise HTTPException(status_code=404, detail="Classroom not found")

    # Normalize input
    if isinstance(payload, list):
        students_raw = payload
    elif isinstance(payload, dict) and "students" in payload:
        students_raw = payload["students"]
    else:
        students_raw = [payload]

    inserted_or_updated = []
    for item in students_raw:
        if isinstance(item, StudentItem):
            roll = item.roll_number.strip()
            name = item.full_name.strip()
            email = item.email.strip() if item.email else None
        elif isinstance(item, dict):
            roll = str(item.get("roll_number", "")).strip()
            name = str(item.get("full_name") or item.get("name", "")).strip()
            email = str(item.get("email", "")).strip() or None
        else:
            continue

        if not roll or not name:
            continue

        existing = (
            db.query(Student)
            .filter(Student.classroom_id == classroom_id, Student.roll_number == roll)
            .first()
        )
        if existing:
            existing.full_name = name
            if email:
                existing.email = email
            inserted_or_updated.append({
                "id": existing.id,
                "classroom_id": classroom_id,
                "roll_number": roll,
                "full_name": name,
                "email": existing.email,
            })
        else:
            st_id = str(uuid.uuid4())
            new_st = Student(
                id=st_id,
                classroom_id=classroom_id,
                roll_number=roll,
                full_name=name,
                email=email,
            )
            db.add(new_st)
            inserted_or_updated.append({
                "id": st_id,
                "classroom_id": classroom_id,
                "roll_number": roll,
                "full_name": name,
                "email": email,
            })

    db.commit()

    # Update student count on Course if linked
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    if crs:
        crs.students_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
        db.commit()

    # Optional cloud sync
    if settings.USE_SUPABASE and inserted_or_updated:
        try:
            supabase.table("students").upsert(inserted_or_updated, on_conflict="classroom_id,roll_number").execute()
        except Exception as e:
            logger.warning(f"Cloud student enrollment sync notice: {e}")

    return {
        "status": "success",
        "total_inserted": len(inserted_or_updated),
        "students": inserted_or_updated,
    }


@router.post("/{classroom_id}/students/upload-csv", response_model=StudentUploadCSVResponse)
async def upload_students_csv(
    classroom_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Accepts a multipart CSV, parses roll_number, name, email, validates duplicates, and inserts."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .csv file.")

    contents = await file.read()
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    csv_file = io.StringIO(text)
    reader = csv.reader(csv_file)
    header = next(reader, None)

    if not header:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    roll_idx = None
    name_idx = None
    email_idx = None

    for idx, col in enumerate(header):
        c = col.strip().lower().replace("_", "").replace(" ", "").replace("-", "")
        if c in ("rollnumber", "rollno", "roll", "studentroll", "id", "roll#"):
            roll_idx = idx
        elif c in ("name", "fullname", "studentname", "names"):
            name_idx = idx
        elif c in ("email", "emailaddress", "studentemail", "mail"):
            email_idx = idx

    if roll_idx is None or name_idx is None:
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain 'roll_number' and 'name' columns. Found columns: {', '.join(header)}",
        )

    # Fetch existing students in local DB
    existing_rolls = {
        s.roll_number.strip()
        for s in db.query(Student).filter(Student.classroom_id == classroom_id).all()
        if s.roll_number
    }

    seen_rolls_in_file = set()
    inserted_records = []
    skipped = []

    for row_num, row in enumerate(reader, start=2):
        if not row or not any(cell.strip() for cell in row):
            continue

        roll = row[roll_idx].strip() if roll_idx < len(row) else ""
        name = row[name_idx].strip() if name_idx < len(row) else ""
        email = row[email_idx].strip() if email_idx is not None and email_idx < len(row) else ""

        if not roll or not name:
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": "Missing roll number or full name",
            })
            continue

        if roll in seen_rolls_in_file:
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": f"Duplicate roll number '{roll}' found in CSV",
            })
            continue

        if roll in existing_rolls:
            skipped.append({
                "row": row_num,
                "roll_number": roll,
                "full_name": name,
                "reason": f"Student with roll number '{roll}' is already enrolled",
            })
            continue

        seen_rolls_in_file.add(roll)
        st_id = str(uuid.uuid4())
        new_student = Student(
            id=st_id,
            classroom_id=classroom_id,
            roll_number=roll,
            full_name=name,
            email=email or None,
        )
        db.add(new_student)
        inserted_records.append({
            "id": st_id,
            "classroom_id": classroom_id,
            "roll_number": roll,
            "full_name": name,
            "email": email or None,
        })

    db.commit()

    # Update course student count
    crs = db.query(Course).filter(Course.id == classroom_id).first()
    if crs:
        crs.students_count = db.query(Student).filter(Student.classroom_id == classroom_id).count()
        db.commit()

    # Optional cloud sync
    if settings.USE_SUPABASE and inserted_records:
        try:
            supabase.table("students").upsert(inserted_records, on_conflict="classroom_id,roll_number").execute()
        except Exception as e:
            logger.warning(f"Cloud CSV roster sync notice: {e}")

    return StudentUploadCSVResponse(
        total_inserted=len(inserted_records),
        total_skipped=len(skipped),
        skipped=skipped,
        inserted=inserted_records,
    )


@router.get("/{classroom_id}/students", response_model=List[StudentResponse])
def get_classroom_students(
    classroom_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve complete enrolled roll call list sorted by roll_number."""
    students = (
        db.query(Student)
        .filter(Student.classroom_id == classroom_id)
        .order_by(Student.roll_number.asc())
        .all()
    )

    # Optional cloud fetch fallback if empty
    if not students and settings.USE_SUPABASE:
        try:
            res = (
                supabase.table("students")
                .select("*")
                .eq("classroom_id", classroom_id)
                .order("roll_number")
                .execute()
            )
            for s_data in (res.data or []):
                new_st = Student(
                    id=str(s_data["id"]),
                    classroom_id=str(s_data["classroom_id"]),
                    roll_number=str(s_data["roll_number"]),
                    full_name=str(s_data["full_name"]),
                    email=s_data.get("email"),
                )
                db.add(new_st)
                students.append(new_st)
            db.commit()
        except Exception as e:
            logger.debug(f"Cloud students fallback query notice: {e}")

    return [
        StudentResponse(
            id=s.id,
            classroom_id=s.classroom_id,
            roll_number=s.roll_number,
            full_name=s.full_name,
            email=s.email,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in students
    ]
