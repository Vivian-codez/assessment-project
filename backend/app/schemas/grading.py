from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


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


class StructuredGradingOutput(BaseModel):
    """Pydantic model used for Gemini structured JSON response schema enforcement."""
    overall_score: float = Field(description="Total calculated score out of 100 based on the rubric criteria")
    criteria_evaluations: List[StructuredCriterionEvaluation] = Field(description="Individual evaluations for each rubric criterion")
    feedback_summary: str = Field(description="Constructive evaluation summary for the student and teacher")
    ai_generated_probability: float = Field(default=15.0, description="Estimated percentage probability that content was AI generated (0-100)")
    peer_to_peer_plagiarism_pct: Optional[float] = Field(default=0.0, description="Peer-to-peer plagiarism percentage")
    ai_plagiarism_pct: Optional[float] = Field(default=0.0, description="AI plagiarism percentage")
    web_plagiarism_pct: Optional[float] = Field(default=0.0, description="Public web plagiarism percentage from live search verification")
    web_sources: Optional[List[dict]] = Field(default_factory=list, description="Detected public web sources with url, title, snippet, match_pct")
    plagiarised_words: Optional[List[str]] = Field(default_factory=list, description="Specific phrases or words identified as plagiarised")
    flags: List[str] = Field(default_factory=list, description="Any detected anomalies, excessive similarity flags, or logic gaps")


class GradeApprovalRequest(BaseModel):
    status: str = "approved"  # "approved"
    final_score: float
    criteria_scores: Optional[List[CriterionScoreSchema]] = None
    teacher_feedback: Optional[str] = None
    action: str = "APPROVE"  # "APPROVE" or "SAVE_EDITS"


class FlagActionRequest(BaseModel):
    action: str  # "CONFIRM_CONCERN" | "DISMISS_FLAG" | "ADD_NOTE"
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
