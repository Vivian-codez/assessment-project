# Module docstring explaining that this file defines report and course analytics schemas
"""Report and Course Analytics schemas supporting Phase 7 Real Analytics Dashboard."""

# Import typing utilities for lists, generic dictionaries, optional types, and any values
from typing import List, Dict, Any, Optional
# Import Pydantic field helper and model validator
from pydantic import Field, model_validator
# Import VerismBaseModel which provides dual-casing serialization and common config
from app.schemas.base import VerismBaseModel


# Schema representing an individual high-level summary metric card in the analytics dashboard
class MetricCard(VerismBaseModel):
    """Represents a high-level KPI card with label, value, progress, and UI color tone."""
    # Descriptive title or label for the metric card (e.g., Average Score)
    label: str = ""
    # Formatted display string value (e.g., 84.5% or 42/50)
    value: str = ""
    # Normalized progress bar value from 0.0 to 1.0 or percentage
    progress: float = 0.0
    # Color tone styling key for UI cards (e.g., emerald, lav, amber)
    tone: str = "default"


# Schema representing an individual KPI card with trend comparison vs previous period
class KPICardItem(VerismBaseModel):
    """Represents a key performance indicator card comparing current vs previous periods."""
    # Machine identifier key for the metric
    key: str = ""
    # Descriptive human-readable title (e.g., "Total Students", "Approved Grades")
    label: str = ""
    # Display value formatted for UI presentation
    value: str = ""
    # Exact numeric count or percentage for mathematical charting
    numeric_value: float = 0.0
    # Trend percentage compared to previous period (e.g., "+12.5%", "-3.2%", "0.0%")
    trend: str = "0.0%"
    # Previous period numeric baseline
    previous_value: float = 0.0
    # Semantic styling tone (e.g., "teal", "sage", "amber", "clay")
    tone: str = "default"


# Schema representing an individual bucket bar in the score distribution histogram
class ScoreDistributionBar(VerismBaseModel):
    """Represents a score distribution bucket bar with dual label and bucket keys for UI safety."""
    # Grade range label for the bucket (e.g., 90-100%, 80-89%)
    label: str = ""
    # Synonymous bucket string expected by some frontend chart components
    bucket: Optional[str] = None
    # Frequency or percentage of students falling into this score bucket
    value: float = 0.0
    # Raw count of submissions in this bucket
    count: int = 0
    # Color accent assigned to this distribution bar
    tone: str = "default"

    # Validator synchronizing label and bucket so neither is ever undefined
    @model_validator(mode="after")
    def sync_label_and_bucket(self) -> "ScoreDistributionBar":
        """Synchronize label and bucket properties so frontend charts never encounter undefined."""
        # Check if bucket is not populated but label is available
        if self.bucket is None and self.label:
            # Mirror label into bucket attribute
            self.bucket = self.label
        # Check if label is empty but bucket is available
        elif not self.label and self.bucket:
            # Mirror bucket into label attribute
            self.label = self.bucket
        # Return self after synchronization
        return self


# Schema representing assignment class average and median trend data point
class AssignmentTrendItem(VerismBaseModel):
    """Represents a longitudinal trend data point for an assignment average and median."""
    # Assignment primary UUID
    assignment_id: str = ""
    # Assignment title
    assignment_title: str = ""
    # Arithmetic mean score achieved by students
    average_score: float = 0.0
    # Median score achieved by students
    median_score: float = 0.0
    # Maximum possible score
    max_score: float = 100.0
    # Submissions count evaluated for this assignment
    submissions_count: int = 0


# Schema representing per-criterion performance average to highlight skill gaps
class CriterionAverageItem(VerismBaseModel):
    """Represents an average mastery score across students for a specific rubric criterion."""
    # Name of the rubric criterion evaluated
    criterion_name: str = ""
    # Average points awarded across student submissions
    average_points: float = 0.0
    # Maximum points possible for this criterion
    max_points: float = 100.0
    # Percentage mastery (average / max * 100)
    percentage: float = 0.0
    # Boolean flag indicating whether this is a weak skill area (<70%)
    weak_area: bool = False


# Schema representing an individual funnel stage in the submission evaluation lifecycle
class FunnelStageItem(VerismBaseModel):
    """Represents a stage in the submission evaluation and approval funnel."""
    # Pipeline stage name (e.g., "Uploaded", "AI Graded", "Reviewed", "Approved")
    stage: str = ""
    # Number of submissions currently at or beyond this stage
    count: int = 0
    # Percentage relative to total expected submissions
    percentage: float = 0.0
    # Synonymous conversion percentage field expected by UI funnel component
    conversion_percentage: Optional[float] = None

    # Model validator synchronizing percentage and conversion_percentage
    @model_validator(mode="after")
    def sync_percentages(self) -> "FunnelStageItem":
        """Synchronize percentage and conversion_percentage for frontend funnel compatibility."""
        # If conversion_percentage is absent, mirror percentage
        if self.conversion_percentage is None:
            # Assign percentage value to conversion_percentage
            self.conversion_percentage = self.percentage
        # Return modified model instance
        return self


# Schema representing top or bottom student performer summary
class PerformerItem(VerismBaseModel):
    """Represents a top or struggling student in cohort insights."""
    # Student primary identifier
    student_id: str = ""
    # Student full name
    student_name: str = ""
    # Student roll number
    student_roll: str = ""
    # Average percentage score across assignments
    average_percentage: float = 0.0
    # Average score field expected by frontend cohort performance cards
    average_score: Optional[float] = None
    # Count of evaluated submissions
    submissions_count: int = 0

    # Model validator synchronizing average_percentage and average_score
    @model_validator(mode="after")
    def sync_average_score(self) -> "PerformerItem":
        """Synchronize average_percentage and average_score so UI cards never show NaN."""
        # If average_score is absent, mirror average_percentage
        if self.average_score is None:
            # Assign percentage to average_score
            self.average_score = self.average_percentage
        # Return updated model instance
        return self


# Schema representing an actionable alert in the Needs Attention list
class NeedsAttentionItem(VerismBaseModel):
    """Represents an alert card in the Action Items / Needs Attention dashboard widget."""
    # Unique item identifier
    id: str = ""
    # Category of alert: low_confidence, flagged_similarity, missing_submission, due_soon
    type: str = "warning"
    # Short summary title
    title: str = ""
    # Detailed explanation
    description: str = ""
    # Severity indicator: high, medium, low
    severity: str = "warning"
    # Target submission or assignment ID to link directly
    link_id: Optional[str] = None
    # Button label for the action card (e.g., "Review", "Open Assignment")
    action_label: Optional[str] = "Review"
    # Target navigation route for the action card (e.g., "review", "grading")
    action_target: Optional[str] = "review"


# Schema representing breakdown of teacher review actions and outcomes
class ReviewOutcome(VerismBaseModel):
    """Represents a review outcome category for teacher decisions."""
    # Action category label (e.g., Approved Unmodified, Teacher Overridden, Flagged)
    label: str = ""
    # Percentage or count of reviews in this outcome category
    value: float = 0.0
    # Hex or CSS color string for chart segment display
    color: str = "#4f46e5"


# Schema representing full aggregated course analytics and reporting dashboard response
class ReportResponse(VerismBaseModel):
    """Complete aggregated course reporting response."""
    # Unique identifier of the course being reported
    course_id: str = ""
    # Title or name of the course
    course_name: str = ""
    # Class section cohort identifier
    section: str = ""
    # List of key summary metric cards displayed at the top of the report
    metrics: List[MetricCard] = Field(default_factory=list)
    # Histogram bars displaying student grade distribution across the course
    score_distribution: List[ScoreDistributionBar] = Field(default_factory=list)
    # Chronological series of floating-point historical assignment class averages
    score_trends: List[float] = Field(default_factory=list)
    # Proportional breakdown of final teacher review decisions
    review_outcomes: List[ReviewOutcome] = Field(default_factory=list)


# Schema representing complete aggregated Phase 7 Analytics response
class AnalyticsResponse(VerismBaseModel):
    """Complete aggregated Phase 7 Analytics response supporting the main teacher dashboard."""
    # Active query filters applied
    filters: Dict[str, Any] = Field(default_factory=dict)
    # High-level KPI metric cards with trends vs previous period
    kpi_cards: List[KPICardItem] = Field(default_factory=list)
    # Real score distribution histogram buckets
    grade_distribution: List[ScoreDistributionBar] = Field(default_factory=list)
    # Historical class average and median progression per assignment
    assignment_trends: List[AssignmentTrendItem] = Field(default_factory=list)
    # Rubric criterion skill gap averages
    criterion_averages: List[CriterionAverageItem] = Field(default_factory=list)
    # Submission pipeline funnel
    funnel: List[FunnelStageItem] = Field(default_factory=list)
    # Synonymous submission_funnel property expected by the frontend
    submission_funnel: Optional[List[FunnelStageItem]] = None
    # On-time vs late submission breakdown
    on_time_stats: Dict[str, Any] = Field(default_factory=dict)
    # Similarity risk breakdown across submissions
    similarity_risk_distribution: List[Dict[str, Any]] = Field(default_factory=list)
    # Grading throughput metrics
    throughput_stats: Dict[str, Any] = Field(default_factory=dict)
    # Top 5 performing students
    top_performers: List[PerformerItem] = Field(default_factory=list)
    # Bottom 5 students needing support
    bottom_performers: List[PerformerItem] = Field(default_factory=list)
    # Actionable items requiring teacher intervention
    needs_attention: List[NeedsAttentionItem] = Field(default_factory=list)
    # Boolean flag indicating whether dataset is empty (for skeleton/guidance states)
    is_empty: bool = False

    # Model validator synchronizing funnel and submission_funnel
    @model_validator(mode="after")
    def sync_submission_funnel(self) -> "AnalyticsResponse":
        """Synchronize funnel and submission_funnel so UI never reads undefined."""
        # If submission_funnel is not provided, populate from funnel
        if self.submission_funnel is None:
            # Assign funnel items to submission_funnel
            self.submission_funnel = self.funnel
        # If funnel is empty but submission_funnel has items, mirror back
        elif not self.funnel and self.submission_funnel:
            # Assign submission_funnel items to funnel
            self.funnel = self.submission_funnel
        # Return updated model instance
        return self
