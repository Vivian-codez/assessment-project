# Module docstring explaining that this file defines report and course analytics schemas
"""Report and Course Analytics schemas."""

# Import typing utilities for lists, generic dictionaries, and any values
from typing import List, Dict, Any
# Import Pydantic base model class
from pydantic import BaseModel


# Schema representing an individual high-level summary metric card in the analytics dashboard
class MetricCard(BaseModel):
    # Descriptive title or label for the metric card (e.g., Average Score)
    label: str
    # Formatted display string value (e.g., 84.5% or 42/50)
    value: str
    # Normalized progress bar value from 0.0 to 1.0 or percentage
    progress: float
    # Color tone styling key for UI cards (e.g., emerald, lav, amber)
    tone: str


# Schema representing an individual bucket bar in the score distribution histogram
class ScoreDistributionBar(BaseModel):
    # Grade range label for the bucket (e.g., 90-100%, 80-89%)
    label: str
    # Frequency or percentage of students falling into this score bucket
    value: float
    # Color accent assigned to this distribution bar
    tone: str


# Schema representing breakdown of teacher review actions and outcomes
class ReviewOutcome(BaseModel):
    # Action category label (e.g., Approved Unmodified, Teacher Overridden, Flagged)
    label: str
    # Percentage or count of reviews in this outcome category
    value: float
    # Hex or CSS color string for chart segment display
    color: str


# Schema representing full aggregated course analytics and reporting dashboard response
class ReportResponse(BaseModel):
    # Unique identifier of the course being reported
    course_id: str
    # Title or name of the course
    course_name: str
    # Class section cohort identifier
    section: str
    # List of key summary metric cards displayed at the top of the report
    metrics: List[MetricCard]
    # Histogram bars displaying student grade distribution across the course
    score_distribution: List[ScoreDistributionBar]
    # Chronological series of floating-point historical assignment class averages
    score_trends: List[float]
    # Proportional breakdown of final teacher review decisions
    review_outcomes: List[ReviewOutcome]
