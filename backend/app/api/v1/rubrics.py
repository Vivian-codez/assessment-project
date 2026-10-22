"""Matrix Rubrics API endpoints connecting with Supabase."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.supabase import supabase
from app.core.logging import logger
from app.schemas.rubric import (
    RubricCreate,
    RubricResponse,
    RubricCriterionSchema,
    RubricLevel,
)
from app.api.v1.auth import get_current_instructor

router = APIRouter(prefix="/rubrics", tags=["Matrix Rubrics"])


def _format_criterion(row: dict) -> RubricCriterionSchema:
    raw_levels = row.get("levels") or []
    levels = []
    if isinstance(raw_levels, list):
        for lvl in raw_levels:
            if isinstance(lvl, dict):
                levels.append(
                    RubricLevel(
                        level_name=lvl.get("level_name", "Tier"),
                        points=float(lvl.get("points", 0.0)),
                        description=lvl.get("description", ""),
                    )
                )

    crit_name = row.get("criterion_name") or row.get("name") or "Criterion"
    max_pts = float(row.get("max_points") or row.get("max_score") or 4.0)

    return RubricCriterionSchema(
        id=str(row["id"]),
        criterion_name=crit_name,
        name=crit_name,
        description=row.get("description") or "",
        weight=float(row.get("weight") or 25.0),
        max_points=max_pts,
        max_score=max_pts,
        order_index=int(row.get("order_index") or 0),
        levels=levels,
    )


def _format_rubric(r_data: dict, criteria_rows: list) -> RubricResponse:
    title = r_data.get("title") or r_data.get("name") or "Untitled Rubric"
    total_marks = float(r_data.get("total_marks") or r_data.get("total_max_score") or 0.0)
    criteria = [_format_criterion(c) for c in criteria_rows]

    return RubricResponse(
        id=str(r_data["id"]),
        title=title,
        name=title,
        classroom_id=str(r_data.get("classroom_id")) if r_data.get("classroom_id") else None,
        course_id=str(r_data.get("course_id") or r_data.get("classroom_id") or ""),
        total_marks=total_marks,
        total_max_score=total_marks,
        created_at=str(r_data.get("created_at") or ""),
        criteria=criteria,
    )


@router.post("", response_model=RubricResponse)
def create_rubric(
    payload: RubricCreate,
    current_instructor = Depends(get_current_instructor),
):
    """Create a new matrix rubric with tiered point descriptions."""
    title = (payload.title or payload.name or "Untitled Rubric").strip()
    classroom_id = payload.classroom_id or payload.course_id

    # Compute total marks
    total_marks = payload.total_marks or payload.total_max_score or 0.0
    if not total_marks and payload.criteria:
        calc_total = 0.0
        for c in payload.criteria:
            if c.max_points is not None:
                calc_total += c.max_points
            elif c.levels:
                calc_total += max(l.points for l in c.levels)
            elif c.max_score is not None:
                calc_total += c.max_score
            else:
                calc_total += 4.0
        total_marks = calc_total

    rubric_id = str(uuid.uuid4())
    rubric_record = {
        "id": rubric_id,
        "title": title,
        "name": title,
        "classroom_id": classroom_id,
        "course_id": classroom_id,
        "total_marks": total_marks,
        "total_max_score": total_marks,
    }

    try:
        supabase.table("rubrics").insert(rubric_record).execute()
    except Exception as e:
        logger.error(f"Error inserting rubric into Supabase: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create rubric: {str(e)}")

    created_criteria = []
    for idx, c in enumerate(payload.criteria):
        crit_id = str(uuid.uuid4())
        crit_name = (c.criterion_name or c.name or f"Criterion {idx + 1}").strip()
        levels_data = [
            lvl.model_dump() if hasattr(lvl, "model_dump") else (lvl.dict() if hasattr(lvl, "dict") else lvl)
            for lvl in c.levels
        ]

        if c.max_points is not None:
            max_pts = c.max_points
        elif levels_data:
            max_pts = max(float(l.get("points", 0.0)) for l in levels_data)
        elif c.max_score is not None:
            max_pts = c.max_score
        else:
            max_pts = 4.0

        crit_record = {
            "id": crit_id,
            "rubric_id": rubric_id,
            "criterion_name": crit_name,
            "name": crit_name,
            "description": c.description or "",
            "max_points": max_pts,
            "max_score": max_pts,
            "order_index": c.order_index if c.order_index is not None else idx,
            "levels": levels_data,
        }
        try:
            supabase.table("rubric_criteria").insert(crit_record).execute()
            created_criteria.append(crit_record)
        except Exception as e:
            logger.warning(f"Error inserting criterion into Supabase: {e}")

    return _format_rubric(rubric_record, created_criteria)


@router.get("", response_model=List[RubricResponse])
def list_rubrics(
    classroom_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve all rubrics, optionally filtered by classroom or course ID."""
    target_id = classroom_id or course_id
    try:
        q = supabase.table("rubrics").select("*")
        if target_id:
            q = q.or_(f"classroom_id.eq.{target_id},course_id.eq.{target_id}")
        res = q.order("created_at", desc=True).execute()
        rubrics_data = res.data or []
    except Exception as e:
        logger.error(f"Error listing rubrics from Supabase: {e}")
        rubrics_data = []

    results = []
    for r in rubrics_data:
        try:
            crit_res = (
                supabase.table("rubric_criteria")
                .select("*")
                .eq("rubric_id", r["id"])
                .order("order_index")
                .execute()
            )
            criteria_rows = crit_res.data or []
        except Exception:
            criteria_rows = []
        results.append(_format_rubric(r, criteria_rows))

    return results


@router.get("/{rubric_id}", response_model=RubricResponse)
def get_rubric(
    rubric_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve a matrix rubric and all its criteria with level descriptions."""
    try:
        res = supabase.table("rubrics").select("*").eq("id", rubric_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Rubric not found")
        rubric_data = res.data[0]

        crit_res = (
            supabase.table("rubric_criteria")
            .select("*")
            .eq("rubric_id", rubric_id)
            .order("order_index")
            .execute()
        )
        criteria_rows = crit_res.data or []
        return _format_rubric(rubric_data, criteria_rows)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rubric {rubric_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/rubrics", response_model=List[RubricResponse])
def get_course_rubrics(
    course_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Retrieve all rubrics for a given course or classroom (backward compatibility)."""
    return list_rubrics(classroom_id=course_id, current_instructor=current_instructor)


@router.delete("/{rubric_id}", status_code=204)
def delete_rubric(
    rubric_id: str,
    current_instructor = Depends(get_current_instructor),
):
    """Delete a rubric and its associated criteria."""
    try:
        supabase.table("rubric_criteria").delete().eq("rubric_id", rubric_id).execute()
        supabase.table("rubrics").delete().eq("id", rubric_id).execute()
        return None
    except Exception as e:
        logger.error(f"Error deleting rubric {rubric_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
