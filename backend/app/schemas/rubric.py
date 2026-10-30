# Module docstring explaining that this file defines rubric schemas supporting the matrix builder format
"""Rubric schemas supporting Matrix Rubric Builder format."""

# Import typing utilities for lists, optional values, any types, and dictionaries
from typing import List, Optional, Any, Dict
# Import Pydantic base model, field helper, and configuration dictionary
from pydantic import BaseModel, Field, ConfigDict


# Schema representing an individual performance level tier within a rubric criterion
class RubricLevel(BaseModel):
    # Configure model to support reading from ORM attributes and mapping by alias
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Name or tier label of this level (e.g., Exemplary, Proficient, Needs Work)
    level_name: str
    # Point value associated with achieving this level
    points: float
    # Detailed descriptive expectations for this achievement level
    description: str


# Schema representing a single rubric criterion with weights and performance levels
class RubricCriterionSchema(BaseModel):
    # Configure model to support reading from ORM attributes and mapping by alias
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Optional unique identifier for this criterion record
    id: Optional[str] = None
    # Criterion title or skill evaluated (e.g., Code Structure)
    criterion_name: Optional[str] = None
    # Name alias for frontend compatibility
    name: Optional[str] = None
    # Optional descriptive guidance for the criterion
    description: Optional[str] = ""
    # Percentage or point weight of this criterion, defaulting to 25.0
    weight: Optional[float] = 25.0
    # Maximum points achievable for this criterion
    max_points: Optional[float] = None
    # Maximum score alias supporting the 'max' field name
    max_score: Optional[float] = Field(default=None, alias="max")
    # Ordinal index for sequencing criteria in the UI, defaulting to 0
    order_index: int = 0
    # Ordered list of distinct performance levels for this criterion
    levels: List[RubricLevel] = []


# Schema for validating incoming requests to create a new rubric
class RubricCreate(BaseModel):
    # Primary title of the rubric
    title: Optional[str] = None
    # Secondary title alias for frontend compatibility
    name: Optional[str] = None
    # Optional classroom identifier linking this rubric
    classroom_id: Optional[str] = None
    # Optional course identifier linking this rubric
    course_id: Optional[str] = None
    # Total sum of marks possible in this rubric
    total_marks: Optional[float] = None
    # Total maximum score alias
    total_max_score: Optional[float] = None
    # List of criteria items composing this rubric
    criteria: List[RubricCriterionSchema] = []


# Schema for returning complete rubric data in API responses
class RubricResponse(BaseModel):
    # Configure model to support reading from ORM attributes and mapping by alias
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Unique string identifier of the rubric
    id: str
    # Primary title of the rubric
    title: str
    # Title alias for frontend compatibility
    name: Optional[str] = None
    # Optional classroom identifier
    classroom_id: Optional[str] = None
    # Optional course identifier
    course_id: Optional[str] = None
    # Total points possible across all criteria in the rubric
    total_marks: float
    # Total maximum score alias
    total_max_score: Optional[float] = None
    # ISO-formatted creation timestamp string
    created_at: Optional[str] = None
    # Complete list of criteria and levels in this rubric
    criteria: List[RubricCriterionSchema] = []
