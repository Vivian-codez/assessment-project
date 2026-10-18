"""Report and Course Analytics schemas."""

from typing import List, Dict, Any
from pydantic import BaseModel


class MetricCard(BaseModel):
    label: str
    value: str
    progress: float
    tone: str


class ScoreDistributionBar(BaseModel):
    label: str
    value: float
    tone: str


class ReviewOutcome(BaseModel):
    label: str
    value: float
    color: str


class ReportResponse(BaseModel):
    course_id: str
    course_name: str
    section: str
    metrics: List[MetricCard]
    score_distribution: List[ScoreDistributionBar]
    score_trends: List[float]
    review_outcomes: List[ReviewOutcome]
