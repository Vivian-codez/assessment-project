"""Classroom Roster & Roll Call Management API endpoints (Supabase)."""

import csv
import io
import uuid
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, status

from app.core.supabase import supabase
from app.core.logging import logger
from app.schemas.classroom import (
    StudentItem,
    StudentResponse,
    StudentUploadCSVResponse,
    ClassroomCreate,
    ClassroomResponse,
)
from app.api.v1.auth import get_current_instructor

router = APIRouter(prefix="/classrooms", tags=["Classrooms & Roll Call"])


@router.get("", response_model=List[ClassroomResponse])
def get_classrooms(
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve all classrooms for the active instructor with live student counts."""
    try:
        q = supabase.table("classrooms").select("*")
        if current_instructor and current_instructor.id:
            res = q.order("created_at", desc=True).execute()
        else:
            res = q.order("created_at", desc=True).execute()
        raw_classrooms = res.data or []
        if not raw_classrooms:
            try:
                c_res = supabase.table("courses").select("*").execute()
                for crs in (c_res.data or []):
                    try:
                        uuid.UUID(str(crs["id"]))
                        raw_classrooms.append({
                            "id": str(crs["id"]),
                            "name": crs["name"],
                            "code": crs["code"],
                            "instructor_id": crs.get("instructor_id"),
                            "created_at": crs.get("created_at"),
                        })
                        supabase.table("classrooms").upsert({
                            "id": str(crs["id"]),
                            "name": crs["name"],
                            "code": crs["code"],
                            "instructor_id": crs.get("instructor_id"),
                        }).execute()
                    except ValueError:
                        continue
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error querying classrooms from Supabase: {e}")
        raw_classrooms = []

    results = []
    for c in raw_classrooms:
        c_id = str(c["id"])
        # Query live enrolled student count
        try:
            count_res = (
                supabase.table("students")
                .select("id", count="exact")
                .eq("classroom_id", c_id)
                .execute()
            )
            count = count_res.count if count_res.count is not None else len(count_res.data or [])
        except Exception:
            count = 0

        results.append(
            ClassroomResponse(
                id=c_id,
                name=c["name"],
                code=c["code"],
                instructor_id=str(c.get("instructor_id") or ""),
                students_count=count,
                created_at=str(c.get("created_at") or ""),
            )
        )
    return results


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    current_instructor = Depends(get_current_instructor),
):
    """Create a new classroom / course for enrollment."""
    c_id = str(uuid.uuid4())
    record = {
        "id": c_id,
        "name": payload.name.strip(),
        "code": payload.code.strip(),
        "instructor_id": current_instructor.id if current_instructor else None,
    }
    try:
        try:
            res = supabase.table("classrooms").insert(record).execute()
        except Exception as insert_err:
            if "violates foreign key constraint" in str(insert_err).lower() and record.get("instructor_id"):
                record["instructor_id"] = None
                res = supabase.table("classrooms").insert(record).execute()
            else:
                raise insert_err

        created = res.data[0] if res.data else record
        try:
            supabase.table("courses").upsert({
                "id": c_id,
                "name": payload.name.strip(),
                "code": payload.code.strip(),
                "section": "A",
                "tone": "lav",
                "students_count": 0,
                "instructor_id": record.get("instructor_id"),
            }).execute()
        except Exception:
            pass
        return ClassroomResponse(
            id=str(created["id"]),
            name=created["name"],
            code=created["code"],
            instructor_id=str(created.get("instructor_id") or ""),
            students_count=0,
            created_at=str(created.get("created_at") or ""),
        )
    except Exception as e:
        logger.error(f"Error creating classroom in Supabase: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create classroom: {str(e)}")


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(
    classroom_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve details for a single classroom."""
    try:
        res = supabase.table("classrooms").select("*").eq("id", classroom_id).execute()
        if not res.data:
            # Also check if matching code or course
            raise HTTPException(status_code=404, detail="Classroom not found")
        c = res.data[0]

        count_res = (
            supabase.table("students")
            .select("id", count="exact")
            .eq("classroom_id", classroom_id)
            .execute()
        )
        count = count_res.count if count_res.count is not None else 0

        return ClassroomResponse(
            id=str(c["id"]),
            name=c["name"],
            code=c["code"],
            instructor_id=str(c.get("instructor_id") or ""),
            students_count=count,
            created_at=str(c.get("created_at") or ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classroom {classroom_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Delete a classroom and cascade delete all its students and rubrics."""
    try:
        supabase.table("students").delete().eq("classroom_id", classroom_id).execute()
        supabase.table("rubrics").delete().eq("classroom_id", classroom_id).execute()
        supabase.table("classrooms").delete().eq("id", classroom_id).execute()
        return None
    except Exception as e:
        logger.error(f"Error deleting classroom {classroom_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Student Roll Call Management
# ==============================================================================

@router.post("/{classroom_id}/students/manual")
def enroll_students_manual(
    classroom_id: str,
    payload: Union[List[StudentItem], Dict[str, Any]] = Body(...),
    current_instructor = Depends(get_current_instructor),
):
    """Batch enroll students into a classroom either one-by-one or multi-line."""
    # Normalize input
    if isinstance(payload, list):
        students_raw = payload
    elif isinstance(payload, dict) and "students" in payload:
        students_raw = payload["students"]
    else:
        students_raw = [payload]

    records = []
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

        if roll and name:
            records.append({
                "id": str(uuid.uuid4()),
                "classroom_id": classroom_id,
                "roll_number": roll,
                "full_name": name,
                "email": email,
            })

    if not records:
        raise HTTPException(status_code=400, detail="No valid student records provided.")

    try:
        # Upsert with constraint uq_students_classroom_roll
        res = (
            supabase.table("students")
            .upsert(records, on_conflict="classroom_id,roll_number")
            .execute()
        )
        return {
            "status": "success",
            "total_inserted": len(res.data or records),
            "students": res.data or records,
        }
    except Exception as e:
        logger.error(f"Error upserting manual students: {e}")
        raise HTTPException(status_code=500, detail=f"Database error during enrollment: {str(e)}")


@router.post("/{classroom_id}/students/upload-csv", response_model=StudentUploadCSVResponse)
async def upload_students_csv(
    classroom_id: str,
    file: UploadFile = File(...),
    current_instructor = Depends(get_current_instructor),
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

    # Fetch existing students to detect already-enrolled duplicates
    try:
        existing_res = (
            supabase.table("students")
            .select("roll_number")
            .eq("classroom_id", classroom_id)
            .execute()
        )
        existing_rolls = {
            str(r["roll_number"]).strip()
            for r in (existing_res.data or [])
            if r.get("roll_number")
        }
    except Exception as e:
        logger.warning(f"Error checking existing students: {e}")
        existing_rolls = set()

    seen_rolls_in_file = set()
    valid_records = []
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
        valid_records.append({
            "id": str(uuid.uuid4()),
            "classroom_id": classroom_id,
            "roll_number": roll,
            "full_name": name,
            "email": email or None,
        })

    inserted_records = []
    if valid_records:
        for i in range(0, len(valid_records), 100):
            batch = valid_records[i : i + 100]
            try:
                ins_res = (
                    supabase.table("students")
                    .upsert(batch, on_conflict="classroom_id,roll_number")
                    .execute()
                )
                if ins_res.data:
                    inserted_records.extend(ins_res.data)
                else:
                    inserted_records.extend(batch)
            except Exception as e:
                logger.error(f"Error upserting CSV batch: {e}")
                for b in batch:
                    skipped.append({
                        "row": "batch",
                        "roll_number": b["roll_number"],
                        "full_name": b["full_name"],
                        "reason": str(e),
                    })

    return StudentUploadCSVResponse(
        total_inserted=len(inserted_records),
        total_skipped=len(skipped),
        skipped=skipped,
        inserted=inserted_records,
    )


@router.get("/{classroom_id}/students", response_model=List[StudentResponse])
def get_classroom_students(
    classroom_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve complete enrolled roll call list sorted by roll_number."""
    try:
        res = (
            supabase.table("students")
            .select("*")
            .eq("classroom_id", classroom_id)
            .order("roll_number")
            .execute()
        )
        students = res.data or []
        return [
            StudentResponse(
                id=str(s["id"]),
                classroom_id=str(s["classroom_id"]),
                roll_number=str(s["roll_number"]),
                full_name=str(s["full_name"]),
                email=s.get("email"),
                created_at=str(s.get("created_at") or ""),
            )
            for s in students
        ]
    except Exception as e:
        logger.error(f"Error getting students for classroom {classroom_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
