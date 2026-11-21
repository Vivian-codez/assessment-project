# Module docstring explaining similarity and cross-submission plagiarism API endpoints
"""Similarity and Cross-Submission Plagiarism API endpoints."""

# Import FastAPI components for routing, dependency injection, HTTP error handling, and query parameters
from fastapi import APIRouter, Depends, HTTPException, Query
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch
# Import Submission database model
from app.models.submission import Submission
# Import Pydantic schemas for similarity overview, pair responses, and student references
from app.schemas.similarity import (
    # Schema serializing overall similarity check report
    SimilarityCheckOverviewResponse,
    # Schema serializing individual pairwise similarity details
    SimilarityPairResponse,
    # Schema serializing student reference identifier and name
    StudentRef,
)

# Initialize FastAPI router instance tagged under Similarity Check
router = APIRouter(tags=["Similarity Check"])


# HTTP GET route handler returning similarity analysis overview for an assignment
@router.get("/assignments/{assignment_id}/similarity", response_model=SimilarityCheckOverviewResponse)
def get_assignment_similarity_overview(
    # Assignment ID string extracted from URL path parameter
    assignment_id: str,
    # Query parameter specifying minimum similarity threshold percentage
    threshold: float = Query(90.0, description="Similarity threshold percentage"),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing similarity overview retrieval
    """Retrieve peer-to-peer similarity checks and flagged pairs for an assignment."""
    # Query count of all submissions submitted for target assignment
    total_submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()

    # Query all pairwise similarity match records recorded for target assignment
    matches = db.query(SimilarityMatch).filter(SimilarityMatch.assignment_id == assignment_id).all()

    # Count number of matches exceeding or equal to configured similarity threshold
    high_sim_count = sum(1 for m in matches if m.similarity_score >= threshold)
    # Count total number of potential matches found
    potential_count = len(matches)

    # Initialize empty list to hold serialized similarity pair responses
    pair_responses = []
    # Iterate through each fetched pairwise similarity match record
    for m in matches:
        # Resolve navigation property for student A submission
        sub_a = m.submission_a
        # Resolve navigation property for student B submission
        sub_b = m.submission_b

        # Resolve student A display name with fallback
        name_a = sub_a.student_name if sub_a else "Student A"
        # Resolve student A roll number with fallback
        roll_a = sub_a.student_roll if sub_a else "2024-001"
        # Resolve student B display name with fallback
        name_b = sub_b.student_name if sub_b else "Student B"
        # Resolve student B roll number with fallback
        roll_b = sub_b.student_roll if sub_b else "2024-002"

        # Append serialized SimilarityPairResponse schema instance
        pair_responses.append(
            # Instantiate SimilarityPairResponse
            SimilarityPairResponse(
                # Set pair ID
                pair_id=m.id,
                # Set legacy student A name
                a=name_a,
                # Set legacy student B name
                b=name_b,
                # Construct structured student A reference
                student_a=StudentRef(id=sub_a.id if sub_a else "", name=name_a, roll=roll_a),
                # Construct structured student B reference
                student_b=StudentRef(id=sub_b.id if sub_b else "", name=name_b, roll=roll_b),
                # Set calculated similarity score float
                similarity=m.similarity_score,
                # Set match status string
                status=m.status,
                # Extract list of matching phrases or default to empty list
                matching_phrases=m.matching_phrases or [],
                # Compute maximum AI content probability across both submissions
                ai_content_probability=max(
                    # Extract submission A AI probability
                    sub_a.ai_content_probability if sub_a else 0.0,
                    # Extract submission B AI probability
                    sub_b.ai_content_probability if sub_b else 0.0,
                ),
            )
        )

    # Return serialized SimilarityCheckOverviewResponse schema instance
    return SimilarityCheckOverviewResponse(
        # Set threshold percentage
        threshold=threshold,
        # Set total submissions count
        total_submissions=total_submissions,
        # Set total checked submissions count
        checked=total_submissions,
        # Set potential similarity pairs count
        potential_similarity=potential_count,
        # Set high similarity pairs count
        high_similarity=high_sim_count,
        # Set list of serialized pairs
        pairs=pair_responses,
    )


# HTTP GET route handler returning side-by-side text comparison for a flagged pair
@router.get("/similarity/pairs/{pair_id}")
def get_pair_comparison_detail(
    # Pair ID string extracted from URL path parameter
    pair_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing side-by-side text comparison retrieval
    """Retrieve side-by-side comparison text for a flagged student pair."""
    # Query database for SimilarityMatch matching pair_id
    match = db.query(SimilarityMatch).filter(SimilarityMatch.id == pair_id).first()
    # Check if match was not found
    if not match:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Similarity pair not found")

    # Resolve navigation property for submission A
    sub_a = match.submission_a
    # Resolve navigation property for submission B
    sub_b = match.submission_b

    # Return detailed dictionary containing comparison attributes and extracted text
    return {
        # Set pair ID
        "pair_id": match.id,
        # Set similarity score float
        "similarity_score": match.similarity_score,
        # Set match status
        "status": match.status,
        # Set matching phrases list
        "matching_phrases": match.matching_phrases,
        # Set teacher justification note
        "teacher_note": match.teacher_note,
        # Construct dictionary of student A submission data
        "student_a": {
            # Set submission ID
            "id": sub_a.id if sub_a else "",
            # Set student name
            "name": sub_a.student_name if sub_a else "Student A",
            # Set roll number
            "roll": sub_a.student_roll if sub_a else "",
            # Set extracted submission text
            "text": sub_a.extracted_text if sub_a else "",
            # Set AI content probability
            "ai_content": sub_a.ai_content_probability if sub_a else 0.0,
        },
        # Construct dictionary of student B submission data
        "student_b": {
            # Set submission ID
            "id": sub_b.id if sub_b else "",
            # Set student name
            "name": sub_b.student_name if sub_b else "Student B",
            # Set roll number
            "roll": sub_b.student_roll if sub_b else "",
            # Set extracted submission text
            "text": sub_b.extracted_text if sub_b else "",
            # Set AI content probability
            "ai_content": sub_b.ai_content_probability if sub_b else 0.0,
        },
    }
