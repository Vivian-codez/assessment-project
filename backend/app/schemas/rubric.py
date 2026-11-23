# Module docstring explaining that this file defines rubric schemas supporting the matrix builder format
"""Rubric schemas supporting Matrix Rubric Builder format."""

# Import typing utilities for lists, optional values, any types, and dictionaries
from typing import List, Optional, Any, Dict
# Import Pydantic base model, field helper, configuration dictionary, and model validator
from pydantic import BaseModel, Field, ConfigDict, model_validator
# Import VerismBaseModel base class supporting dual camelCase and snake_case keys
from app.schemas.base import VerismBaseModel


# Schema representing an individual performance level tier within a rubric criterion
class RubricLevel(VerismBaseModel):
    # Name or tier label of this level (e.g., Exemplary, Proficient, Needs Work)
    level_name: str
    # Point value associated with achieving this level
    points: float = 0.0
    # Detailed descriptive expectations for this achievement level
    description: str = ""


# Schema representing a single rubric criterion with weights and performance levels
class RubricCriterionSchema(VerismBaseModel):
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
    max_points: Optional[float] = 25.0
    # Maximum score alias supporting the 'max' field name
    max_score: Optional[float] = Field(default=25.0, alias="max")
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
class RubricResponse(VerismBaseModel):
    # Unique string identifier of the rubric
    id: str
    # Primary title of the rubric
    title: str = "Standard Matrix Rubric"
    # Title alias for frontend compatibility
    name: Optional[str] = None
    # Optional classroom identifier
    classroom_id: Optional[str] = None
    # Optional course identifier
    course_id: Optional[str] = None
    # Total points possible across all criteria in the rubric
    total_marks: float = 100.0
    # Total maximum score alias
    total_max_score: Optional[float] = 100.0
    # ISO-formatted creation timestamp string
    created_at: Optional[str] = None
    # Complete list of criteria and levels in this rubric
    criteria: List[RubricCriterionSchema] = []

    # Model validator synchronizing title and name
    @model_validator(mode="after")
    def sync_title_and_name(self) -> "RubricResponse":
        """Synchronize title and name so both are populated."""
        if not self.title and self.name:
            self.title = self.name
        elif not self.name and self.title:
            self.name = self.title
        return self


# Schema for returning parsed rubric file output for teacher review in Step 3 wizard
class Phase3ParsedRubricResponse(VerismBaseModel):
    # Title extracted from document
    title: str = Field(default="Parsed Matrix Rubric", description="Extracted rubric title")
    # Total marks computed from criteria
    total_marks: float = Field(default=100.0, description="Total maximum score")
    # List of parsed criteria with descending tiers
    criteria: List[RubricCriterionSchema] = Field(default_factory=list, description="Extracted criteria and tiers")
    # Raw extracted text preview
    extracted_text_preview: str = Field(default="", description="Snippet of raw text extracted from file")

