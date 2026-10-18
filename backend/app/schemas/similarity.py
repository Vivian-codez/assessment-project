"""Similarity and Peer-to-Peer Cross-Submission Plagiarism Schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class StudentRef(BaseModel):
    id: str
    name: str
    roll: str


class SimilarityPairResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    pair_id: str
    a: str = Field(description="Student A display name")
    b: str = Field(description="Student B display name")
    student_a: Optional[StudentRef] = None
    student_b: Optional[StudentRef] = None
    score: float = Field(alias="similarity", description="Similarity score percentage")
    status: str = "Within range"
    matching_phrases: List[str] = Field(default_factory=list)
    ai_content_probability: float = 0.0


class SimilarityCheckOverviewResponse(BaseModel):
    threshold: float = 90.0
    total_submissions: int
    checked: int
    potential_similarity: int
    high_similarity: int
    pairs: List[SimilarityPairResponse]
