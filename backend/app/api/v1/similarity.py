"""Similarity and Cross-Submission Plagiarism API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.similarity_match import SimilarityMatch
from app.models.submission import Submission
from app.schemas.similarity import (
    SimilarityCheckOverviewResponse,
    SimilarityPairResponse,
    StudentRef,
)

router = APIRouter(tags=["Similarity Check"])


@router.get("/assignments/{assignment_id}/similarity", response_model=SimilarityCheckOverviewResponse)
def get_assignment_similarity_overview(
    assignment_id: str,
    threshold: float = Query(90.0, description="Similarity threshold percentage"),
    db: Session = Depends(get_db),
):
    """Retrieve peer-to-peer similarity checks and flagged pairs for an assignment."""
    total_submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()

    matches = db.query(SimilarityMatch).filter(SimilarityMatch.assignment_id == assignment_id).all()

    high_sim_count = sum(1 for m in matches if m.similarity_score >= threshold)
    potential_count = len(matches)

    pair_responses = []
    for m in matches:
        sub_a = m.submission_a
        sub_b = m.submission_b

        name_a = sub_a.student_name if sub_a else "Student A"
        roll_a = sub_a.student_roll if sub_a else "2024-001"
        name_b = sub_b.student_name if sub_b else "Student B"
        roll_b = sub_b.student_roll if sub_b else "2024-002"

        pair_responses.append(
            SimilarityPairResponse(
                pair_id=m.id,
                a=name_a,
                b=name_b,
                student_a=StudentRef(id=sub_a.id if sub_a else "", name=name_a, roll=roll_a),
                student_b=StudentRef(id=sub_b.id if sub_b else "", name=name_b, roll=roll_b),
                similarity=m.similarity_score,
                status=m.status,
                matching_phrases=m.matching_phrases or [],
                ai_content_probability=max(
                    sub_a.ai_content_probability if sub_a else 0.0,
                    sub_b.ai_content_probability if sub_b else 0.0,
                ),
            )
        )

    return SimilarityCheckOverviewResponse(
        threshold=threshold,
        total_submissions=total_submissions,
        checked=total_submissions,
        potential_similarity=potential_count,
        high_similarity=high_sim_count,
        pairs=pair_responses,
    )


@router.get("/similarity/pairs/{pair_id}")
def get_pair_comparison_detail(
    pair_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve side-by-side comparison text for a flagged student pair."""
    match = db.query(SimilarityMatch).filter(SimilarityMatch.id == pair_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Similarity pair not found")

    sub_a = match.submission_a
    sub_b = match.submission_b

    return {
        "pair_id": match.id,
        "similarity_score": match.similarity_score,
        "status": match.status,
        "matching_phrases": match.matching_phrases,
        "teacher_note": match.teacher_note,
        "student_a": {
            "id": sub_a.id if sub_a else "",
            "name": sub_a.student_name if sub_a else "Student A",
            "roll": sub_a.student_roll if sub_a else "",
            "text": sub_a.extracted_text if sub_a else "",
            "ai_content": sub_a.ai_content_probability if sub_a else 0.0,
        },
        "student_b": {
            "id": sub_b.id if sub_b else "",
            "name": sub_b.student_name if sub_b else "Student B",
            "roll": sub_b.student_roll if sub_b else "",
            "text": sub_b.extracted_text if sub_b else "",
            "ai_content": sub_b.ai_content_probability if sub_b else 0.0,
        },
    }
