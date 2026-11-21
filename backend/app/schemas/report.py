# Module docstring explaining that this file defines report and course analytics schemas
"""Report and Course Analytics schemas supporting Phase 7 Real Analytics Dashboard."""

# Import typing utilities for lists, generic dictionaries, optional types, and any values
from typing import List, Dict, Any, Optional
# Import Pydantic base model class and Field helper
from pydantic import BaseModel, Field


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


# Schema representing an individual KPI card with trend comparison vs previous period
class KPICardItem(BaseModel):
    # Machine identifier key for the metric
    key: str
    # Descriptive human-readable title (e.g., "Total Students", "Approved Grades")
    label: str
    # Display value formatted for UI presentation
    value: str
    # Exact numeric count or percentage for mathematical charting
    numeric_value: float
    # Trend percentage compared to previous period (e.g., "+12.5%", "-3.2%", "0.0%")
    trend: str
    # Previous period numeric baseline
    previous_value: float
    # Semantic styling tone (e.g., "teal", "sage", "amber", "clay")
    tone: str


# Schema representing an individual bucket bar in the score distribution histogram
class ScoreDistributionBar(BaseModel):
    # Grade range label for the bucket (e.g., 90-100%, 80-89%)
    label: str
    # Frequency or percentage of students falling into this score bucket
    value: float
    # Raw count of submissions in this bucket
    count: int = 0
    # Color accent assigned to this distribution bar
    tone: str


# Schema representing assignment class average and median trend data point
class AssignmentTrendItem(BaseModel):
    # Assignment primary UUID
    assignment_id: str
    # Assignment title
    assignment_title: str
    # Arithmetic mean score achieved by students
    average_score: float
    # Median score achieved by students
    median_score: float
    # Maximum possible score
    max_score: float
    # Submissions count evaluated for this assignment
    submissions_count: int


# Schema representing per-criterion performance average to highlight skill gaps
class CriterionAverageItem(BaseModel):
    # Name of the rubric criterion evaluated
    criterion_name: str
    # Average points awarded across student submissions
    average_points: float
    # Maximum points possible for this criterion
    max_points: float
    # Percentage mastery (average / max * 100)
    percentage: float
    # Boolean flag indicating whether this is a weak skill area (<70%)
    weak_area: bool = False


# Schema representing an individual funnel stage in the submission evaluation lifecycle
class FunnelStageItem(BaseModel):
    # Pipeline stage name (e.g., "Uploaded", "AI Graded", "Reviewed", "Approved")
    stage: str
    # Number of submissions currently at or beyond this stage
    count: int
    # Percentage relative to total expected submissions
    percentage: float


# Schema representing top or bottom student performer summary
class PerformerItem(BaseModel):
    # Student primary identifier
    student_id: str
    # Student full name
    student_name: str
    # Student roll number
    student_roll: str
    # Average percentage score across assignments
    average_percentage: float
    # Count of evaluated submissions
    submissions_count: int


# Schema representing an actionable alert in the Needs Attention list
class NeedsAttentionItem(BaseModel):
    # Unique item identifier
    id: str
    # Category of alert: low_confidence, flagged_similarity, missing_submission, due_soon
    type: str
    # Short summary title
    title: str
    # Detailed explanation
    description: str
    # Severity indicator: high, medium, low
    severity: str
    # Target submission or assignment ID to link directly
    link_id: Optional[str] = None


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


# Schema representing complete aggregated Phase 7 Analytics response
class AnalyticsResponse(BaseModel):
    # Active query filters applied
    filters: Dict[str, Any]
    # High-level KPI metric cards with trends vs previous period
    kpi_cards: List[KPICardItem]
    # Real score distribution histogram buckets
    grade_distribution: List[ScoreDistributionBar]
    # Historical class average and median progression per assignment
    assignment_trends: List[AssignmentTrendItem]
    # Rubric criterion skill gap averages
    criterion_averages: List[CriterionAverageItem]
    # Submission pipeline funnel
    funnel: List[FunnelStageItem]
    # On-time vs late submission breakdown
    on_time_stats: Dict[str, Any]
    # Similarity risk breakdown across submissions
    similarity_risk_distribution: List[Dict[str, Any]]
    # Grading throughput metrics
    throughput_stats: Dict[str, Any]
    # Top 5 performing students
    top_performers: List[PerformerItem]
    # Bottom 5 students needing support
    bottom_performers: List[PerformerItem]
    # Actionable items requiring teacher intervention
    needs_attention: List[NeedsAttentionItem]
    # Boolean flag indicating whether dataset is empty (for skeleton/guidance states)
    is_empty: bool = False
