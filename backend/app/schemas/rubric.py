"""Rubric schemas supporting Matrix Rubric Builder format."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class RubricLevel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    level_name: str
    points: float
    description: str


class RubricCriterionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[str] = None
    criterion_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = ""
    weight: Optional[float] = 25.0
    max_points: Optional[float] = None
    max_score: Optional[float] = Field(default=None, alias="max")
    order_index: int = 0
    levels: List[RubricLevel] = []


class RubricCreate(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    classroom_id: Optional[str] = None
    course_id: Optional[str] = None
    total_marks: Optional[float] = None
    total_max_score: Optional[float] = None
    criteria: List[RubricCriterionSchema] = []


class RubricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str
    name: Optional[str] = None
    classroom_id: Optional[str] = None
    course_id: Optional[str] = None
    total_marks: float
    total_max_score: Optional[float] = None
    created_at: Optional[str] = None
    criteria: List[RubricCriterionSchema] = []
