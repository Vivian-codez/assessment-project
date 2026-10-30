"""Matrix Rubrics API endpoints connecting with database and optional cloud sync."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.supabase import supabase
from app.core.logging import logger
from app.models.rubric import Rubric, RubricCriterion
from app.models.course import Course
from app.models.classroom import Classroom
from app.schemas.rubric import (
    RubricCreate,
    RubricResponse,
    RubricCriterionSchema,
    RubricLevel,
)
from app.api.v1.auth import get_current_instructor
from app.models.instructor import Instructor

router = APIRouter(prefix="/rubrics", tags=["Matrix Rubrics"])


def _format_criterion(crit: RubricCriterion) -> RubricCriterionSchema:
    raw_levels = crit.levels or []
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

    crit_name = crit.criterion_name or crit.name or "Criterion"
    max_pts = float(crit.max_points if crit.max_points is not None else (crit.max_score or 4.0))

    return RubricCriterionSchema(
        id=crit.id,
        criterion_name=crit_name,
        name=crit_name,
        description=crit.description or "",
        weight=float(crit.weight if crit.weight is not None else 25.0),
        max_points=max_pts,
        max_score=max_pts,
        order_index=int(crit.order_index or 0),
        levels=levels,
    )


def _format_rubric(rubric: Rubric) -> RubricResponse:
    title = rubric.title or rubric.name or "Untitled Rubric"
    total_marks = float(rubric.total_marks if rubric.total_marks is not None else (rubric.total_max_score or 100.0))
    criteria = [_format_criterion(c) for c in (rubric.criteria or [])]

    return RubricResponse(
        id=rubric.id,
        title=title,
        name=title,
        classroom_id=rubric.classroom_id,
        course_id=rubric.course_id or rubric.classroom_id or "",
        total_marks=total_marks,
        total_max_score=total_marks,
        created_at=rubric.created_at.isoformat() if rubric.created_at else "",
        criteria=criteria,
    )


@router.post("", response_model=RubricResponse)
def create_rubric(
    payload: RubricCreate,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Create a new matrix rubric with tiered point descriptions."""
    title = (payload.title or payload.name or "Untitled Rubric").strip()
    target_id = payload.classroom_id or payload.course_id

    # Compute total marks
    total_marks = payload.total_marks or payload.total_max_score or 0.0
    if not total_marks and payload.criteria:
        calc_total = 0.0
        for c in payload.criteria:
            if c.max_points is not None:
                calc_total += c.max_points
            elif c.levels:
                calc_total += max((float(l.points) for l in c.levels), default=4.0)
            elif c.max_score is not None:
                calc_total += c.max_score
            else:
                calc_total += 4.0
        total_marks = calc_total

    rubric_id = str(uuid.uuid4())

    new_rubric = Rubric(
        id=rubric_id,
        title=title,
        name=title,
        classroom_id=target_id,
        course_id=target_id,
        total_marks=total_marks,
        total_max_score=total_marks,
    )
    db.add(new_rubric)

    for idx, c in enumerate(payload.criteria or []):
        crit_id = str(uuid.uuid4())
        crit_name = (c.criterion_name or c.name or f"Criterion {idx + 1}").strip()
        levels_data = [
            lvl.model_dump() if hasattr(lvl, "model_dump") else (lvl.dict() if hasattr(lvl, "dict") else lvl)
            for lvl in (c.levels or [])
        ]

        if c.max_points is not None:
            max_pts = float(c.max_points)
        elif levels_data:
            max_pts = max((float(l.get("points", 0.0)) for l in levels_data), default=4.0)
        elif c.max_score is not None:
            max_pts = float(c.max_score)
        else:
            max_pts = 4.0

        new_crit = RubricCriterion(
            id=crit_id,
            rubric_id=rubric_id,
            criterion_name=crit_name,
            name=crit_name,
            description=c.description or "",
            weight=float(c.weight if c.weight is not None else 25.0),
            max_points=max_pts,
            max_score=max_pts,
            order_index=c.order_index if c.order_index is not None else idx,
            levels=levels_data,
        )
        db.add(new_crit)

    db.commit()
    db.refresh(new_rubric)

    # Optional cloud sync if enabled
    if settings.USE_SUPABASE:
        try:
            supabase.table("rubrics").upsert({
                "id": rubric_id,
                "title": title,
                "name": title,
                "classroom_id": target_id,
                "course_id": target_id,
                "total_marks": total_marks,
                "total_max_score": total_marks,
            }).execute()
            for crit in new_rubric.criteria:
                supabase.table("rubric_criteria").upsert({
                    "id": crit.id,
                    "rubric_id": rubric_id,
                    "criterion_name": crit.criterion_name,
                    "name": crit.name,
                    "description": crit.description,
                    "max_points": crit.max_points,
                    "max_score": crit.max_score,
                    "order_index": crit.order_index,
                    "levels": crit.levels,
                }).execute()
        except Exception as e:
            logger.warning(f"Cloud rubric sync notice: {e}")

    return _format_rubric(new_rubric)


@router.get("", response_model=List[RubricResponse])
def list_rubrics(
    classroom_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all rubrics, optionally filtered by classroom or course ID."""
    target_id = classroom_id or course_id
    query = db.query(Rubric)
    if target_id:
        query = query.filter(
            (Rubric.classroom_id == target_id) | (Rubric.course_id == target_id)
        )
    rubrics = query.order_by(Rubric.created_at.desc()).all()

    # Optional cloud sync fallback if local DB has none and cloud active
    if not rubrics and settings.USE_SUPABASE:
        try:
            q = supabase.table("rubrics").select("*")
            if target_id:
                q = q.or_(f"classroom_id.eq.{target_id},course_id.eq.{target_id}")
            res = q.order("created_at", desc=True).execute()
            for r_row in (res.data or []):
                new_r = Rubric(
                    id=str(r_row["id"]),
                    title=r_row.get("title") or r_row.get("name"),
                    name=r_row.get("name") or r_row.get("title"),
                    classroom_id=r_row.get("classroom_id"),
                    course_id=r_row.get("course_id"),
                    total_marks=float(r_row.get("total_marks") or r_row.get("total_max_score") or 0.0),
                    total_max_score=float(r_row.get("total_max_score") or r_row.get("total_marks") or 100.0),
                )
                db.add(new_r)
                rubrics.append(new_r)
            db.commit()
        except Exception as e:
            logger.debug(f"Cloud rubric sync fallback notice: {e}")

    return [_format_rubric(r) for r in rubrics]


@router.get("/{rubric_id}", response_model=RubricResponse)
def get_rubric(
    rubric_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve a matrix rubric and all its criteria with level descriptions."""
    r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return _format_rubric(r)


@router.get("/courses/{course_id}/rubrics", response_model=List[RubricResponse])
def get_course_rubrics(
    course_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve all rubrics for a given course or classroom (backward compatibility)."""
    return list_rubrics(classroom_id=course_id, course_id=course_id, db=db, current_instructor=current_instructor)


@router.delete("/{rubric_id}", status_code=204)
def delete_rubric(
    rubric_id: str,
    db: Session = Depends(get_db),
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Delete a rubric and its associated criteria."""
    r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rubric not found")

    db.delete(r)
    db.commit()

    if settings.USE_SUPABASE:
        try:
            supabase.table("rubric_criteria").delete().eq("rubric_id", rubric_id).execute()
            supabase.table("rubrics").delete().eq("id", rubric_id).execute()
        except Exception as e:
            logger.warning(f"Cloud rubric delete notice: {e}")

    return None
