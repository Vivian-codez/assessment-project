# Module docstring explaining that this file defines schemas for AI Grading, integrity audits, and teacher review queues
"""Pydantic schemas for AI Grading, 3-Way Plagiarism Audits, and Teacher Review Queue."""

# Import datetime utility for timestamp operations
from datetime import datetime
# Import typing utilities for lists, optionals, dictionaries, and any type
from typing import List, Optional, Dict, Any
# Import Pydantic base model, field helper, configuration dictionary, and model validator decorator
from pydantic import BaseModel, Field, ConfigDict, model_validator


# Schema representing an individual criterion score and rationale
class CriterionScoreSchema(BaseModel):
    # Name of the rubric criterion evaluated
    criterion_name: str
    # Numeric score awarded for this criterion
    score: float
    # Optional maximum points possible for this criterion
    max: Optional[float] = None
    # Optional explanation or rationale justifying the score
    rationale: Optional[str] = None


# Schema for structured criterion evaluation with required fields
class StructuredCriterionEvaluation(BaseModel):
    # Name of the rubric criterion
    criterion_name: str
    # Exact points awarded for this criterion
    awarded_score: float
    # Maximum points possible for this criterion
    max_score: float
    # Justification text explaining why this score was awarded
    rationale: str


# Schema summarizing overall grading calculations and letter grade
class GradingSummary(BaseModel):
    # Total score awarded across all criteria
    score: float = Field(default=0.0, description="Total score awarded")
    # Total maximum points achievable
    max_points: float = Field(default=100.0, description="Maximum total points")
    # Normalized overall percentage grade from 0 to 100
    percentage: float = Field(default=0.0, description="Overall percentage (0-100)")
    # Letter grade corresponding to the percentage
    grade: str = Field(default="B", description="Letter grade (e.g., A, B+, C)")


# Schema for individual rubric breakdown item in hierarchical grading
class RubricBreakdownItem(BaseModel):
    # Name of the rubric criterion
    criterion_name: str
    # Points awarded for this criterion
    awarded_points: float
    # Maximum points possible for this criterion
    max_points: float
    # Qualitative justification based on rubric criteria
    rationale: str


# Schema for peer-to-peer plagiarism analysis results
class PeerPlagiarismAudit(BaseModel):
    # Peer similarity percentage score between 0 and 100
    similarity_percentage: float = Field(default=0.0, description="Peer-to-peer similarity score percentage (0-100)")
    # Optional identifier of the most similar peer submission in the class
    matched_peer_id: Optional[str] = Field(default=None, description="Identifier of the most similar peer submission")
    # List of verbatim or closely matching excerpt strings
    matching_excerpts: List[str] = Field(default_factory=list, description="Extracted matching or identical sentences/blocks")


# Schema representing an external web source match found during plagiarism check
class WebSourceItem(BaseModel):
    # URL of the matched public online source
    url: str
    # Optional title of the matched webpage
    title: Optional[str] = None
    # Optional snippet or passage matching the student submission
    snippet: Optional[str] = None
    # Percentage similarity match to this specific web source
    match_pct: Optional[float] = 0.0


# Schema for web search grounded plagiarism audit
class WebPlagiarismAudit(BaseModel):
    # Overall similarity percentage against public web sources
    similarity_percentage: float = Field(default=0.0, description="Public web search grounded similarity percentage (0-100)")
    # List of matched external web source items with URLs and snippets
    matched_sources: List[WebSourceItem] = Field(default_factory=list, description="Public URLs and matching snippets from web grounding")


# Schema assessing synthetic or AI-generated content probability
class AIContentAssessment(BaseModel):
    # Qualitative categorical rating of AI authorship likelihood
    likelihood_rating: str = Field(default="Low", description="Rating: Low, Moderate, or High likelihood of AI authorship")
    # Estimated numeric probability percentage of AI generation
    ai_probability: float = Field(default=0.0, description="Probability percentage of synthetic/AI generation (0-100)")
    # List of stylistic hallmarks or patterns indicating AI generation
    stylistic_indicators: List[str] = Field(default_factory=list, description="Specific stylistic artifacts or patterns observed")


# Schema aggregating peer, web, and AI integrity audit metrics
class IntegrityAudit(BaseModel):
    # Peer-to-peer similarity audit component
    peer_plagiarism: PeerPlagiarismAudit = Field(default_factory=PeerPlagiarismAudit)
    # Public web search grounding audit component
    web_plagiarism: WebPlagiarismAudit = Field(default_factory=WebPlagiarismAudit)
    # AI generation and synthetic writing assessment component
    ai_content_assessment: AIContentAssessment = Field(default_factory=AIContentAssessment)


# Schema containing qualitative feedback highlights and overall evaluation summary
class FeedbackDetails(BaseModel):
    # List of key strengths identified in the student's work
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified in the submission")
    # List of actionable recommendations and areas for improvement
    actionable_corrections: List[str] = Field(default_factory=list, description="Specific corrections and recommendations")
    # Comprehensive summary paragraph synthesizing the evaluation
    summary: str = Field(default="", description="Overall evaluation summary")


# Comprehensive schema enforcing Gemini LLM structured JSON response output
class StructuredGradingOutput(BaseModel):
    # Class docstring explaining dual support for hierarchical and flat attributes
    """Pydantic model used for Gemini structured JSON response schema enforcement.

    Supports both the hierarchical schema (grading_summary, rubric_breakdown, integrity_audit, feedback)
    and flat convenience attributes for backward compatibility across the codebase.
    """
    # Optional nested grading summary container
    grading_summary: Optional[GradingSummary] = None
    # Optional nested list of rubric breakdown items
    rubric_breakdown: Optional[List[RubricBreakdownItem]] = None
    # Optional nested three-way academic integrity audit container
    integrity_audit: Optional[IntegrityAudit] = None
    # Optional nested qualitative feedback details container
    feedback: Optional[FeedbackDetails] = None

    # Backward compatibility flat total score attribute
    overall_score: float = Field(default=0.0, description="Total calculated score out of 100 based on the rubric criteria")
    # Backward compatibility flat list of criteria evaluations
    criteria_evaluations: List[StructuredCriterionEvaluation] = Field(default_factory=list, description="Individual evaluations for each rubric criterion")
    # Backward compatibility flat evaluation summary string
    feedback_summary: str = Field(default="", description="Constructive evaluation summary for the student and teacher")
    # Backward compatibility flat AI generation probability percentage
    ai_generated_probability: float = Field(default=15.0, description="Estimated percentage probability that content was AI generated (0-100)")
    # Backward compatibility flat peer-to-peer plagiarism percentage
    peer_to_peer_plagiarism_pct: Optional[float] = Field(default=0.0, description="Peer-to-peer plagiarism percentage")
    # Backward compatibility flat AI plagiarism percentage alias
    ai_plagiarism_pct: Optional[float] = Field(default=0.0, description="AI plagiarism percentage")
    # Backward compatibility flat web search plagiarism percentage
    web_plagiarism_pct: Optional[float] = Field(default=0.0, description="Public web plagiarism percentage from live search verification")
    # Backward compatibility flat list of detected web source dictionaries
    web_sources: Optional[List[dict]] = Field(default_factory=list, description="Detected public web sources with url, title, snippet, match_pct")
    # Backward compatibility flat list of flagged verbatim plagiarized phrases
    plagiarised_words: Optional[List[str]] = Field(default_factory=list, description="Specific phrases or words identified as plagiarised")
    # List of flag labels identifying detected anomalies or logic gaps
    flags: List[str] = Field(default_factory=list, description="Any detected anomalies, excessive similarity flags, or logic gaps")

    # Model validator ensuring bidirectional synchronization between nested and flat fields
    @model_validator(mode="after")
    def sync_nested_and_flat_fields(self):
        # Check if the nested grading summary object exists
        if self.grading_summary:
            # If the flat overall score is missing or zero, synchronize from the nested summary score
            if not self.overall_score or self.overall_score == 0.0:
                # Assign the nested score to the flat overall score attribute
                self.overall_score = self.grading_summary.score

        # Check if nested rubric breakdown is populated but flat criteria evaluations list is empty
        if self.rubric_breakdown and not self.criteria_evaluations:
            # Populate flat criteria evaluations by converting each rubric breakdown item
            self.criteria_evaluations = [
                # Instantiate structured criterion evaluation model
                StructuredCriterionEvaluation(
                    # Copy criterion name
                    criterion_name=rb.criterion_name,
                    # Copy awarded score
                    awarded_score=rb.awarded_points,
                    # Copy maximum score
                    max_score=rb.max_points,
                    # Copy rationale text
                    rationale=rb.rationale,
                )
                # Iterate over all items in the rubric breakdown list
                for rb in self.rubric_breakdown
            ]

        # Check if nested feedback container is present
        if self.feedback:
            # If flat feedback summary is empty but nested summary exists, assign it directly
            if not self.feedback_summary and self.feedback.summary:
                # Copy nested summary string to flat summary attribute
                self.feedback_summary = self.feedback.summary
            # Otherwise if flat feedback summary is empty, assemble it from strengths and corrections
            elif not self.feedback_summary:
                # Initialize empty list to accumulate feedback text sections
                parts = []
                # Check if strengths list has entries
                if self.feedback.strengths:
                    # Append formatted strengths string
                    parts.append("Strengths: " + "; ".join(self.feedback.strengths))
                # Check if actionable corrections list has entries
                if self.feedback.actionable_corrections:
                    # Append formatted corrections string
                    parts.append("Corrections: " + "; ".join(self.feedback.actionable_corrections))
                # Join sections with spaces or fallback to default completion message
                self.feedback_summary = " ".join(parts) or "Evaluation complete."

        # Check if nested integrity audit container is present
        if self.integrity_audit:
            # Create local reference to integrity audit container
            ia = self.integrity_audit
            # Check if peer plagiarism audit section exists
            if ia.peer_plagiarism:
                # Copy peer similarity percentage to flat attribute
                self.peer_to_peer_plagiarism_pct = ia.peer_plagiarism.similarity_percentage
                # If excerpts exist and flat plagiarised words is empty, copy excerpts
                if ia.peer_plagiarism.matching_excerpts and not self.plagiarised_words:
                    # Assign matching excerpts to plagiarised words list
                    self.plagiarised_words = ia.peer_plagiarism.matching_excerpts
            # Check if web plagiarism audit section exists
            if ia.web_plagiarism:
                # Copy web similarity percentage to flat attribute
                self.web_plagiarism_pct = ia.web_plagiarism.similarity_percentage
                # If matched sources exist, convert each model to a dictionary for flat list
                if ia.web_plagiarism.matched_sources:
                    # Dump each web source model to standard dictionary
                    self.web_sources = [s.model_dump() for s in ia.web_plagiarism.matched_sources]
            # Check if AI content assessment section exists
            if ia.ai_content_assessment:
                # Copy AI probability to primary flat attribute
                self.ai_generated_probability = ia.ai_content_assessment.ai_probability
                # Copy AI probability to secondary plagiarism percentage alias
                self.ai_plagiarism_pct = ia.ai_content_assessment.ai_probability

        # Check if nested grading summary is missing but flat overall score is available
        if not self.grading_summary and self.overall_score:
            # Capture the overall score percentage
            pct = self.overall_score
            # Determine appropriate letter grade based on standard percentage thresholds
            letter = "A" if pct >= 90 else ("B" if pct >= 80 else ("C" if pct >= 70 else ("D" if pct >= 60 else "F")))
            # Construct nested grading summary object from flat metrics
            self.grading_summary = GradingSummary(score=self.overall_score, max_points=100.0, percentage=pct, grade=letter)

        # Check if nested rubric breakdown is missing but flat criteria evaluations exist
        if not self.rubric_breakdown and self.criteria_evaluations:
            # Populate nested rubric breakdown by converting flat criteria evaluations
            self.rubric_breakdown = [
                # Instantiate rubric breakdown item
                RubricBreakdownItem(
                    # Copy criterion name
                    criterion_name=ce.criterion_name,
                    # Copy awarded points
                    awarded_points=ce.awarded_score,
                    # Copy maximum points
                    max_points=ce.max_score,
                    # Copy rationale text
                    rationale=ce.rationale,
                )
                # Iterate over all flat criteria evaluations
                for ce in self.criteria_evaluations
            ]

        # Check if nested integrity audit container is missing
        if not self.integrity_audit:
            # Instantiate complete nested integrity audit from flat attributes
            self.integrity_audit = IntegrityAudit(
                # Construct peer plagiarism section
                peer_plagiarism=PeerPlagiarismAudit(
                    # Use flat peer plagiarism percentage or default to 0.0
                    similarity_percentage=self.peer_to_peer_plagiarism_pct or 0.0,
                    # Use flat plagiarised words or default to empty list
                    matching_excerpts=self.plagiarised_words or [],
                ),
                # Construct web plagiarism section
                web_plagiarism=WebPlagiarismAudit(
                    # Use flat web plagiarism percentage or default to 0.0
                    similarity_percentage=self.web_plagiarism_pct or 0.0,
                    # Reconstruct WebSourceItem instances from dictionary list
                    matched_sources=[WebSourceItem(**s) for s in (self.web_sources or []) if isinstance(s, dict) and "url" in s],
                ),
                # Construct AI content assessment section
                ai_content_assessment=AIContentAssessment(
                    # Set rating to Moderate if probability is 40% or higher, otherwise Low
                    likelihood_rating="Moderate" if (self.ai_generated_probability or 0) >= 40 else "Low",
                    # Use flat AI generated probability or default to 0.0
                    ai_probability=self.ai_generated_probability or 0.0,
                ),
            )

        # Check if nested feedback container is missing
        if not self.feedback:
            # Construct nested feedback details using flat feedback summary
            self.feedback = FeedbackDetails(
                # Fallback to default evaluation string if feedback summary is empty
                summary=self.feedback_summary or "Evaluation completed against rubric benchmark.",
            )

        # Return validated self instance with all fields synchronized
        return self


# Schema for validating teacher grade approval or override requests
class GradeApprovalRequest(BaseModel):
    # New approval status string, defaulting to approved
    status: str = "approved"
    # Final confirmed numerical score awarded by the teacher
    final_score: float
    # Optional customized list of criterion score adjustments
    criteria_scores: Optional[List[CriterionScoreSchema]] = None
    # Optional qualitative feedback note written by the teacher
    teacher_feedback: Optional[str] = None
    # Action verb describing the teacher's decision, defaulting to APPROVE
    action: str = "APPROVE"


# Schema for teacher actions on flagged submissions (e.g. resolve flag or dismiss)
class FlagActionRequest(BaseModel):
    # Action type string (e.g. resolve, escalate, dismiss)
    action: str
    # Optional explanatory note accompanying the flag action
    note: Optional[str] = None


# Schema for returning draft grade records from API endpoints
class DraftGradeResponse(BaseModel):
    # Enable reading attributes from ORM model instances
    model_config = ConfigDict(from_attributes=True)

    # Unique string identifier for the draft grade record
    id: str
    # Identifier of the submission to which this grade belongs
    submission_id: str
    # AI-recommended score for the submission
    suggested_score: float
    # Final teacher-approved score, or None if pending review
    final_score: Optional[float] = None
    # List of individual criteria score breakdowns stored as JSON dictionaries
    criteria_scores: List[dict]
    # Detailed AI-generated feedback string
    ai_feedback: Optional[str] = None
    # Optional instructor notes or custom feedback
    teacher_feedback: Optional[str] = None
    # Review workflow status (e.g., pending_review, approved, flagged)
    status: str
    # Name and version of the AI model used to generate the evaluation
    ai_model: str
    # Timestamp when the instructor approved the grade
    approved_at: Optional[datetime] = None


# Schema for individual criterion evaluation within an evaluation result
class CriterionEvaluationItem(BaseModel):
    # Name of the rubric criterion evaluated
    criterion_name: str = Field(description="Name of the rubric criterion evaluated")
    # Score awarded for this criterion
    score: float = Field(description="Score awarded for this criterion")
    # Maximum points possible for this criterion, defaulting to 25.0
    max_score: float = Field(default=25.0, description="Maximum points possible for this criterion")
    # Qualitative justification based on rubric level and student work
    rationale: str = Field(description="Qualitative justification based on rubric level and student work")


# Schema representing the three-way academic integrity audit report
class PlagiarismReport(BaseModel):
    # Peer-to-peer similarity score percentage (0-100)
    peer_to_peer_score: float = Field(default=0.0, description="Peer-to-peer similarity score percentage (0-100)")
    # Public web search grounding similarity percentage (0-100)
    public_source_score: float = Field(default=0.0, description="Public web grounding similarity percentage (0-100)")
    # AI-generated text likelihood percentage (0-100)
    ai_probability: float = Field(default=0.0, description="AI-generated text likelihood percentage (0-100)")
    # Specific overlapping sentences, phrases, or matched peer IDs
    flagged_matches: List[str] = Field(default_factory=list, description="Specific overlapping sentences, phrases or matched peer IDs")


# Schema representing complete evaluation results combining scores, rubric breakdown, integrity, and feedback
class EvaluationResult(BaseModel):
    # Total awarded score across all criteria
    total_score: float = Field(description="Total awarded score across all criteria")
    # Total maximum possible score for the assignment, defaulting to 100.0
    max_score: float = Field(default=100.0, description="Total maximum possible score")
    # Breakdown of points and notes per rubric criterion
    criteria_breakdown: List[CriterionEvaluationItem] = Field(default_factory=list, description="Breakdown of points and notes per rubric criterion")
    # 3-way academic integrity report detailing peer, web, and AI metrics
    plagiarism_report: PlagiarismReport = Field(default_factory=PlagiarismReport, description="3-way academic integrity report")
    # Actionable qualitative feedback for the student summarizing strengths and corrections
    feedback: str = Field(default="", description="Actionable qualitative feedback for the student summarizing strengths and corrections")

