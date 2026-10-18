"""Rubric schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RubricCriterionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[str] = None
    name: str  # e.g., "Understanding"
    description: Optional[str] = ""
    weight: float = 25.0
    max_score: float = Field(default=25.0, alias="max")
    order_index: int = 0


class RubricCreate(BaseModel):
    name: str
    course_id: str
    criteria: List[RubricCriterionSchema]
    total_max_score: float = 100.0


class RubricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    course_id: str
    total_max_score: float
    criteria: List[RubricCriterionSchema]
