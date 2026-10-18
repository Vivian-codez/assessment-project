"""Rubrics API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rubric import Rubric, RubricCriterion
from app.schemas.rubric import RubricCreate, RubricResponse, RubricCriterionSchema

router = APIRouter(prefix="/rubrics", tags=["Rubrics"])


@router.get("/courses/{course_id}/rubrics", response_model=List[RubricResponse])
def get_course_rubrics(course_id: str, db: Session = Depends(get_db)):
    """Retrieve all rubrics for a given course."""
    rubrics = db.query(Rubric).filter(Rubric.course_id == course_id).all()
    results = []
    for rubric in rubrics:
        criteria = [
            RubricCriterionSchema(
                id=c.id,
                name=c.name,
                description=c.description or "",
                weight=c.weight,
                max=c.max_score,
                order_index=c.order_index,
            )
            for c in rubric.criteria
        ]
        results.append(
            RubricResponse(
                id=rubric.id,
                name=rubric.name,
                course_id=rubric.course_id,
                total_max_score=rubric.total_max_score,
                criteria=criteria,
            )
        )
    return results


@router.get("/{rubric_id}", response_model=RubricResponse)
def get_rubric(rubric_id: str, db: Session = Depends(get_db)):
    """Retrieve a rubric and all its criteria."""
    rubric = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    criteria = [
        RubricCriterionSchema(
            id=c.id,
            name=c.name,
            description=c.description or "",
            weight=c.weight,
            max=c.max_score,
            order_index=c.order_index,
        )
        for c in rubric.criteria
    ]

    return RubricResponse(
        id=rubric.id,
        name=rubric.name,
        course_id=rubric.course_id,
        total_max_score=rubric.total_max_score,
        criteria=criteria,
    )


@router.post("", response_model=RubricResponse)
def create_rubric(payload: RubricCreate, db: Session = Depends(get_db)):
    """Create a new rubric with criteria rows."""
    rubric_id = f"rub_{uuid.uuid4().hex[:8]}"
    rubric = Rubric(
        id=rubric_id,
        name=payload.name,
        course_id=payload.course_id,
        total_max_score=payload.total_max_score,
    )
    db.add(rubric)

    for idx, c in enumerate(payload.criteria):
        crit = RubricCriterion(
            id=f"crit_{uuid.uuid4().hex[:8]}",
            rubric_id=rubric_id,
            name=c.name,
            description=c.description,
            weight=c.weight,
            max_score=c.max_score,
            order_index=idx,
        )
        db.add(crit)

    db.commit()
    db.refresh(rubric)

    criteria = [
        RubricCriterionSchema(
            id=c.id,
            name=c.name,
            description=c.description or "",
            weight=c.weight,
            max=c.max_score,
            order_index=c.order_index,
        )
        for c in rubric.criteria
    ]

    return RubricResponse(
        id=rubric.id,
        name=rubric.name,
        course_id=rubric.course_id,
        total_max_score=rubric.total_max_score,
        criteria=criteria,
    )
