"""Pydantic schemas for AI Grading, 3-Way Plagiarism Audits, and Teacher Review Queue."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class CriterionScoreSchema(BaseModel):
    criterion_name: str
    score: float
    max: Optional[float] = None
    rationale: Optional[str] = None


class StructuredCriterionEvaluation(BaseModel):
    criterion_name: str
    awarded_score: float
    max_score: float
    rationale: str


class GradingSummary(BaseModel):
    score: float = Field(default=0.0, description="Total score awarded")
    max_points: float = Field(default=100.0, description="Maximum total points")
    percentage: float = Field(default=0.0, description="Overall percentage (0-100)")
    grade: str = Field(default="B", description="Letter grade (e.g., A, B+, C)")


class RubricBreakdownItem(BaseModel):
    criterion_name: str
    awarded_points: float
    max_points: float
    rationale: str


class PeerPlagiarismAudit(BaseModel):
    similarity_percentage: float = Field(default=0.0, description="Peer-to-peer similarity score percentage (0-100)")
    matched_peer_id: Optional[str] = Field(default=None, description="Identifier of the most similar peer submission")
    matching_excerpts: List[str] = Field(default_factory=list, description="Extracted matching or identical sentences/blocks")


class WebSourceItem(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    match_pct: Optional[float] = 0.0


class WebPlagiarismAudit(BaseModel):
    similarity_percentage: float = Field(default=0.0, description="Public web search grounded similarity percentage (0-100)")
    matched_sources: List[WebSourceItem] = Field(default_factory=list, description="Public URLs and matching snippets from web grounding")


class AIContentAssessment(BaseModel):
    likelihood_rating: str = Field(default="Low", description="Rating: Low, Moderate, or High likelihood of AI authorship")
    ai_probability: float = Field(default=0.0, description="Probability percentage of synthetic/AI generation (0-100)")
    stylistic_indicators: List[str] = Field(default_factory=list, description="Specific stylistic artifacts or patterns observed")


class IntegrityAudit(BaseModel):
    peer_plagiarism: PeerPlagiarismAudit = Field(default_factory=PeerPlagiarismAudit)
    web_plagiarism: WebPlagiarismAudit = Field(default_factory=WebPlagiarismAudit)
    ai_content_assessment: AIContentAssessment = Field(default_factory=AIContentAssessment)


class FeedbackDetails(BaseModel):
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified in the submission")
    actionable_corrections: List[str] = Field(default_factory=list, description="Specific corrections and recommendations")
    summary: str = Field(default="", description="Overall evaluation summary")


class StructuredGradingOutput(BaseModel):
    """Pydantic model used for Gemini structured JSON response schema enforcement.

    Supports both the hierarchical schema (grading_summary, rubric_breakdown, integrity_audit, feedback)
    and flat convenience attributes for backward compatibility across the codebase.
    """
    grading_summary: Optional[GradingSummary] = None
    rubric_breakdown: Optional[List[RubricBreakdownItem]] = None
    integrity_audit: Optional[IntegrityAudit] = None
    feedback: Optional[FeedbackDetails] = None

    # Backward compatibility flat attributes
    overall_score: float = Field(default=0.0, description="Total calculated score out of 100 based on the rubric criteria")
    criteria_evaluations: List[StructuredCriterionEvaluation] = Field(default_factory=list, description="Individual evaluations for each rubric criterion")
    feedback_summary: str = Field(default="", description="Constructive evaluation summary for the student and teacher")
    ai_generated_probability: float = Field(default=15.0, description="Estimated percentage probability that content was AI generated (0-100)")
    peer_to_peer_plagiarism_pct: Optional[float] = Field(default=0.0, description="Peer-to-peer plagiarism percentage")
    ai_plagiarism_pct: Optional[float] = Field(default=0.0, description="AI plagiarism percentage")
    web_plagiarism_pct: Optional[float] = Field(default=0.0, description="Public web plagiarism percentage from live search verification")
    web_sources: Optional[List[dict]] = Field(default_factory=list, description="Detected public web sources with url, title, snippet, match_pct")
    plagiarised_words: Optional[List[str]] = Field(default_factory=list, description="Specific phrases or words identified as plagiarised")
    flags: List[str] = Field(default_factory=list, description="Any detected anomalies, excessive similarity flags, or logic gaps")

    @model_validator(mode="after")
    def sync_nested_and_flat_fields(self):
        # 1. Sync from nested to flat if nested is present
        if self.grading_summary:
            if not self.overall_score or self.overall_score == 0.0:
                self.overall_score = self.grading_summary.score

        if self.rubric_breakdown and not self.criteria_evaluations:
            self.criteria_evaluations = [
                StructuredCriterionEvaluation(
                    criterion_name=rb.criterion_name,
                    awarded_score=rb.awarded_points,
                    max_score=rb.max_points,
                    rationale=rb.rationale,
                )
                for rb in self.rubric_breakdown
            ]

        if self.feedback:
            if not self.feedback_summary and self.feedback.summary:
                self.feedback_summary = self.feedback.summary
            elif not self.feedback_summary:
                parts = []
                if self.feedback.strengths:
                    parts.append("Strengths: " + "; ".join(self.feedback.strengths))
                if self.feedback.actionable_corrections:
                    parts.append("Corrections: " + "; ".join(self.feedback.actionable_corrections))
                self.feedback_summary = " ".join(parts) or "Evaluation complete."

        if self.integrity_audit:
            ia = self.integrity_audit
            if ia.peer_plagiarism:
                self.peer_to_peer_plagiarism_pct = ia.peer_plagiarism.similarity_percentage
                if ia.peer_plagiarism.matching_excerpts and not self.plagiarised_words:
                    self.plagiarised_words = ia.peer_plagiarism.matching_excerpts
            if ia.web_plagiarism:
                self.web_plagiarism_pct = ia.web_plagiarism.similarity_percentage
                if ia.web_plagiarism.matched_sources:
                    self.web_sources = [s.model_dump() for s in ia.web_plagiarism.matched_sources]
            if ia.ai_content_assessment:
                self.ai_generated_probability = ia.ai_content_assessment.ai_probability
                self.ai_plagiarism_pct = ia.ai_content_assessment.ai_probability

        # 2. Sync from flat to nested if nested is missing
        if not self.grading_summary and self.overall_score:
            pct = self.overall_score
            letter = "A" if pct >= 90 else ("B" if pct >= 80 else ("C" if pct >= 70 else ("D" if pct >= 60 else "F")))
            self.grading_summary = GradingSummary(score=self.overall_score, max_points=100.0, percentage=pct, grade=letter)

        if not self.rubric_breakdown and self.criteria_evaluations:
            self.rubric_breakdown = [
                RubricBreakdownItem(
                    criterion_name=ce.criterion_name,
                    awarded_points=ce.awarded_score,
                    max_points=ce.max_score,
                    rationale=ce.rationale,
                )
                for ce in self.criteria_evaluations
            ]

        if not self.integrity_audit:
            self.integrity_audit = IntegrityAudit(
                peer_plagiarism=PeerPlagiarismAudit(
                    similarity_percentage=self.peer_to_peer_plagiarism_pct or 0.0,
                    matching_excerpts=self.plagiarised_words or [],
                ),
                web_plagiarism=WebPlagiarismAudit(
                    similarity_percentage=self.web_plagiarism_pct or 0.0,
                    matched_sources=[WebSourceItem(**s) for s in (self.web_sources or []) if isinstance(s, dict) and "url" in s],
                ),
                ai_content_assessment=AIContentAssessment(
                    likelihood_rating="Moderate" if (self.ai_generated_probability or 0) >= 40 else "Low",
                    ai_probability=self.ai_generated_probability or 0.0,
                ),
            )

        if not self.feedback:
            self.feedback = FeedbackDetails(
                summary=self.feedback_summary or "Evaluation completed against rubric benchmark.",
            )

        return self


class GradeApprovalRequest(BaseModel):
    status: str = "approved"
    final_score: float
    criteria_scores: Optional[List[CriterionScoreSchema]] = None
    teacher_feedback: Optional[str] = None
    action: str = "APPROVE"


class FlagActionRequest(BaseModel):
    action: str
    note: Optional[str] = None


class DraftGradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    suggested_score: float
    final_score: Optional[float] = None
    criteria_scores: List[dict]
    ai_feedback: Optional[str] = None
    teacher_feedback: Optional[str] = None
    status: str
    ai_model: str
    approved_at: Optional[datetime] = None
