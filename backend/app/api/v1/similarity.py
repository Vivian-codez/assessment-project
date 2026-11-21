# Module docstring explaining similarity, integrity matrix, case report, and cross-submission plagiarism API endpoints
"""Similarity and Cross-Submission Integrity API Endpoints.

Implements Phase 6 specifications:
- Deterministic-first peer similarity (winnowing, tokenization, shingling, embeddings).
- Configurable thresholds from Assignment model (default 70.0%).
- Pairwise similarity matrix/heatmap endpoint (/assignments/{id}/similarity-matrix).
- Comprehensive exportable integrity case report (/submissions/{id}/integrity-case-report).
- Integrity flag lifecycle updates (/similarity/flags/{id} with new/reviewing/cleared/confirmed).
- On-demand assignment integrity scan endpoint (/assignments/{id}/run-integrity-check).
"""

# Import standard library uuid module for unique ID generation
import uuid
# Import typing annotations for lists, dictionaries, optionals, and any types
from typing import Any, Dict, List, Optional
# Import FastAPI components for routing, dependency injection, HTTP exceptions, query parameters, body schemas, and status codes
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
# Import Session from SQLAlchemy ORM for database operations
from sqlalchemy.orm import Session

# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import application logging utility
from app.core.logging import logger
# Import Assignment database model
from app.models.assignment import Assignment
# Import SimilarityMatch database model
from app.models.similarity_match import SimilarityMatch
# Import Submission database model
from app.models.submission import Submission
# Import IntegrityFlag database model
from app.models.integrity_flag import IntegrityFlag
# Import Instructor database model and current instructor dependency
from app.models.instructor import Instructor
from app.api.v1.auth import get_current_instructor
# Import integrity service singleton
from app.services.integrity_service import integrity_service
# Import Gemini service singleton
from app.services.gemini_service import gemini_service
# Import Pydantic schemas for similarity overview, pair responses, and student references
from app.schemas.similarity import (
    SimilarityCheckOverviewResponse,
    SimilarityPairResponse,
    StudentRef,
)

# Initialize FastAPI router instance tagged under Similarity & Integrity
router = APIRouter(tags=["Similarity & Integrity"])


# HTTP GET route handler returning similarity analysis overview for an assignment
@router.get("/assignments/{assignment_id}/similarity", response_model=SimilarityCheckOverviewResponse)
def get_assignment_similarity_overview(
    # Assignment ID string extracted from URL path parameter
    assignment_id: str,
    # Query parameter specifying minimum similarity threshold percentage (optional, falls back to assignment threshold)
    threshold: Optional[float] = Query(None, description="Similarity threshold percentage"),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing similarity overview retrieval
    """Retrieve peer-to-peer similarity checks and flagged pairs for an assignment."""
    # Query local database for assignment
    assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Resolve threshold using assignment's configured similarity_threshold or fallback 70.0%
    active_threshold = threshold if threshold is not None else (assign.similarity_threshold if assign and assign.similarity_threshold else 70.0)

    # Query count of all submissions submitted for target assignment
    total_submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).count()

    # Query all pairwise similarity match records recorded for target assignment
    matches = db.query(SimilarityMatch).filter(SimilarityMatch.assignment_id == assignment_id).all()

    # Count number of matches exceeding or equal to configured similarity threshold
    high_sim_count = sum(1 for m in matches if m.similarity_score >= active_threshold)
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

    # Return serialized SimilarityCheckOverviewResponse schema instance
    return SimilarityCheckOverviewResponse(
        threshold=active_threshold,
        total_submissions=total_submissions,
        checked=total_submissions,
        potential_similarity=potential_count,
        high_similarity=high_sim_count,
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


# HTTP GET route handler returning complete pairwise similarity heatmap matrix
@router.get("/assignments/{assignment_id}/similarity-matrix")
def get_assignment_similarity_matrix(
    # Assignment ID parameter from path
    assignment_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing similarity matrix generation
    """Returns pairwise similarity heatmap matrix across all submissions for an assignment."""
    # Query all submissions for target assignment
    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    # If fewer than 2 submissions, return empty matrix
    if len(submissions) < 2:
        # Return empty matrix payload
        return {"nodes": [], "links": [], "threshold": 70.0, "matrix": []}

    # Query assignment to check configured threshold
    assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Resolve threshold
    threshold = assign.similarity_threshold if assign and assign.similarity_threshold else 70.0

    # Build nodes list
    nodes = [
        {
            "id": s.id,
            "name": s.student_name or f"Student {idx+1}",
            "roll": s.student_roll or f"Roll-{idx+1}",
            "ai_prob": s.ai_content_probability or 0.0,
        }
        for idx, s in enumerate(submissions)
    ]

    # Query all existing similarity matches for assignment
    existing_matches = db.query(SimilarityMatch).filter(SimilarityMatch.assignment_id == assignment_id).all()
    # Map (sub_a_id, sub_b_id) -> SimilarityMatch
    match_map = {}
    # Iterate through matches
    for m in existing_matches:
        # Key sorted pair
        pair_key = tuple(sorted([m.submission_a_id, m.submission_b_id]))
        # Store match in map
        match_map[pair_key] = m

    # Build links list and NxN matrix
    links = []
    matrix_rows = []

    # Iterate over submissions outer loop
    for i, sub_i in enumerate(submissions):
        # Initialize row list for submission i
        row = []
        # Iterate over submissions inner loop
        for j, sub_j in enumerate(submissions):
            # Check if comparing submission with itself
            if i == j:
                # 100% self similarity on diagonal
                row.append(100.0)
            else:
                # Key sorted pair
                pair_key = tuple(sorted([sub_i.id, sub_j.id]))
                # Check if match exists in database
                m = match_map.get(pair_key)
                # Resolve score
                score = m.similarity_score if m else 0.0
                # Append score to row
                row.append(score)

                # Add link if i < j (avoid duplicate directed links)
                if i < j and score >= threshold:
                    # Append link item
                    links.append({
                        "source": sub_i.id,
                        "target": sub_j.id,
                        "source_name": sub_i.student_name or f"Student {i+1}",
                        "target_name": sub_j.student_name or f"Student {j+1}",
                        "similarity": score,
                        "status": m.status if m else "Flagged",
                        "matched_phrases": m.matching_phrases if m else [],
                    })
        # Append row to matrix
        matrix_rows.append(row)

    # Return complete heatmap matrix structure
    return {
        "assignment_id": assignment_id,
        "threshold": threshold,
        "nodes": nodes,
        "links": sorted(links, key=lambda x: x["similarity"], reverse=True),
        "matrix": matrix_rows,
    }


# HTTP GET route handler returning structured academic integrity case report for a submission
@router.get("/submissions/{submission_id}/integrity-case-report")
def get_submission_integrity_case_report(
    # Submission ID parameter from path
    submission_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing integrity case report retrieval
    """Generates structured metadata for an exportable academic integrity case report."""
    # Query database for target submission
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    # Check if submission was not found
    if not sub:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Submission not found")

    # Query parent assignment
    assign = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    # Resolve assignment title
    assign_title = assign.title if assign else "Assignment"

    # Query integrity flag associated with submission
    flag = db.query(IntegrityFlag).filter(IntegrityFlag.submission_id == submission_id).first()
    # Build flag data dictionary
    flag_data = {
        "status": flag.status if flag else "new",
        "teacher_notes": flag.resolution_note if flag else "",
        "threshold": assign.similarity_threshold if assign else 70.0,
    }

    # Query top similarity match for submission
    top_match = (
        db.query(SimilarityMatch)
        .filter((SimilarityMatch.submission_a_id == submission_id) | (SimilarityMatch.submission_b_id == submission_id))
        .order_by(SimilarityMatch.similarity_score.desc())
        .first()
    )

    # Build comparison details dictionary
    comparison_details = {
        "similarity_score": top_match.similarity_score if top_match else 0.0,
        "algorithmic_score": top_match.similarity_score if top_match else 0.0,
        "matched_segments": top_match.matching_phrases if top_match else [],
    }

    # Check if top match exists and has high score to generate LLM explanation
    llm_explanation = None
    # Check if match score is high
    if top_match and top_match.similarity_score >= (assign.similarity_threshold if assign else 70.0):
        # Resolve peer submission
        peer_id = top_match.submission_b_id if top_match.submission_a_id == submission_id else top_match.submission_a_id
        # Query peer submission
        peer_sub = db.query(Submission).filter(Submission.id == peer_id).first()
        # Generate neutral explanation with Gemini
        llm_explanation = gemini_service.explain_integrity_overlap_with_gemini(
            submission_a_text=sub.extracted_text or "",
            submission_b_text=peer_sub.extracted_text if peer_sub else "",
            matched_segments=top_match.matching_phrases or [],
            student_a_label=sub.student_name or "Target Student",
            student_b_label=peer_sub.student_name if peer_sub else "Peer Student",
        )

    # Generate and return case report
    return integrity_service.generate_case_report(
        submission_id=sub.id,
        student_name=sub.student_name or "Student",
        student_roll=sub.student_roll or "N/A",
        assignment_title=assign_title,
        flag_data=flag_data,
        comparison_details=comparison_details,
        llm_explanation=llm_explanation,
    )


# HTTP PATCH route handler updating an integrity flag's status and teacher notes
@router.patch("/similarity/flags/{flag_id}")
def update_integrity_flag_status(
    # Flag ID string parameter from path
    flag_id: str,
    # JSON payload dictionary containing status and notes
    payload: Dict[str, Any] = Body(...),
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing flag status update
    """Updates an academic integrity flag lifecycle status (new, reviewing, cleared, confirmed) and teacher notes."""
    # Query database for target flag by ID
    flag = db.query(IntegrityFlag).filter(IntegrityFlag.id == flag_id).first()
    # Check if flag exists
    if not flag:
        # Check SimilarityMatch fallback
        match = db.query(SimilarityMatch).filter(SimilarityMatch.id == flag_id).first()
        # If match exists, update teacher note and status on match
        if match:
            # Update status if provided
            if "status" in payload:
                # Update status
                match.status = payload["status"]
            # Update teacher note if provided
            if "teacher_notes" in payload or "teacher_note" in payload:
                # Update note
                match.teacher_note = payload.get("teacher_notes") or payload.get("teacher_note")
            # Commit update
            db.commit()
            # Return updated match payload
            return {"id": match.id, "status": match.status, "teacher_note": match.teacher_note}
        # Raise HTTP 404 exception
        raise HTTPException(status_code=404, detail="Integrity flag not found")

    # Validate status transition
    new_status = payload.get("status")
    # Check if status was provided
    if new_status:
        # Verify status is one of the allowed lifecycle states
        if new_status not in ["new", "reviewing", "cleared", "confirmed"]:
            # Raise HTTP 400 Bad Request exception
            raise HTTPException(status_code=400, detail="Invalid status. Must be one of: new, reviewing, cleared, confirmed")
        # Update flag status
        flag.status = new_status
        # Set resolved boolean if cleared or confirmed
        flag.resolved = new_status in ["cleared", "confirmed"]

    # Check for teacher notes update
    if "teacher_notes" in payload or "resolution_note" in payload:
        # Update resolution note
        flag.resolution_note = payload.get("teacher_notes") or payload.get("resolution_note")

    # Record resolving instructor ID
    if current_instructor and current_instructor.id:
        # Set resolved_by
        flag.resolved_by = current_instructor.id

    # Commit changes to database
    db.commit()
    # Refresh flag entity
    db.refresh(flag)

    # Return updated flag details
    return {
        "id": flag.id,
        "submission_id": flag.submission_id,
        "status": flag.status,
        "resolved": flag.resolved,
        "resolution_note": flag.resolution_note,
        "severity": flag.severity,
    }


# HTTP POST route handler triggering an on-demand integrity and plagiarism scan across an assignment
@router.post("/assignments/{assignment_id}/run-integrity-check")
def trigger_assignment_integrity_check(
    # Assignment ID parameter from path
    assignment_id: str,
    # Injected database session dependency
    db: Session = Depends(get_db),
    # Authenticated instructor dependency
    current_instructor: Instructor = Depends(get_current_instructor),
):
    # Route docstring describing on-demand integrity scan
    """Executes deterministic plagiarism and similarity scan across all submissions in an assignment.

    Excludes teacher starter code and common boilerplate. Calls Gemini neutral explanation for pairs exceeding threshold.
    """
    # Query database for assignment
    assign = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    # Check if assignment exists
    if not assign:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Resolve threshold from assignment model
    threshold = assign.similarity_threshold if assign.similarity_threshold is not None else 70.0
    # Resolve starter code to exclude
    starter_code = assign.starter_code or assign.description or ""

    # Query all submissions for assignment
    submissions = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    # If fewer than 2 submissions, return notice
    if len(submissions) < 2:
        # Return notice
        return {
            "status": "completed",
            "message": "At least 2 submissions are required to run pairwise similarity analysis.",
            "pairs_evaluated": 0,
            "flags_created": 0,
        }

    # Initialize counters
    pairs_evaluated = 0
    flags_created = 0

    # Iterate over submissions in pairs
    for i in range(len(submissions)):
        for j in range(i + 1, len(submissions)):
            # Get submission A
            sub_a = submissions[i]
            # Get submission B
            sub_j = submissions[j]
            # Increment evaluated pairs
            pairs_evaluated += 1

            # Extract text from both submissions
            text_a = sub_a.extracted_text or ""
            text_b = sub_j.extracted_text or ""

            # Check if either submission is empty
            if not text_a.strip() or not text_b.strip():
                # Skip empty text
                continue

            # Run deterministic comparison with starter code excluded
            res = integrity_service.compare_submissions(
                text_a=text_a,
                text_b=text_b,
                starter_code=starter_code,
                is_code=(assign.assignment_type == "code" or "def " in text_a or "function " in text_a),
            )
            # Extract combined similarity score
            sim_score = float(res.get("similarity_score", 0.0))
            # Extract matched segments
            matched_phrases = res.get("matched_segments", [])

            # Check if match already exists in database
            pair_match = (
                db.query(SimilarityMatch)
                .filter(
                    ((SimilarityMatch.submission_a_id == sub_a.id) & (SimilarityMatch.submission_b_id == sub_j.id))
                    | ((SimilarityMatch.submission_a_id == sub_j.id) & (SimilarityMatch.submission_b_id == sub_a.id))
                )
                .first()
            )

            # Determine status label
            status_label = "High similarity" if sim_score >= threshold else "Acceptable"

            # If match exists, update score and phrases
            if pair_match:
                # Update similarity score
                pair_match.similarity_score = sim_score
                # Update matched phrases
                pair_match.matching_phrases = matched_phrases
                # Update status
                pair_match.status = status_label
            else:
                # Create new SimilarityMatch model
                new_match = SimilarityMatch(
                    id=f"sm_{uuid.uuid4().hex[:12]}",
                    assignment_id=assignment_id,
                    submission_a_id=sub_a.id,
                    submission_b_id=sub_j.id,
                    similarity_score=sim_score,
                    matching_phrases=matched_phrases,
                    status=status_label,
                )
                # Add match to session
                db.add(new_match)

            # If similarity exceeds threshold, generate or update IntegrityFlag
            if sim_score >= threshold:
                # Check for existing flag on submission A
                flag_a = db.query(IntegrityFlag).filter(
                    (IntegrityFlag.submission_id == sub_a.id) & (IntegrityFlag.flag_type == "peer_similarity")
                ).first()
                # Create flag if not present
                if not flag_a:
                    # Instantiate IntegrityFlag
                    flag_a = IntegrityFlag(
                        submission_id=sub_a.id,
                        flag_type="peer_similarity",
                        severity="high" if sim_score >= 85.0 else "medium",
                        description=f"Peer similarity score of {sim_score}% detected with {sub_j.student_name or 'Peer Student'}.",
                        details={"peer_submission_id": sub_j.id, "similarity_score": sim_score, "matched_phrases": matched_phrases},
                        status="new",
                    )
                    # Add flag to session
                    db.add(flag_a)
                    # Increment counter
                    flags_created += 1

                # Check for existing flag on submission B
                flag_b = db.query(IntegrityFlag).filter(
                    (IntegrityFlag.submission_id == sub_j.id) & (IntegrityFlag.flag_type == "peer_similarity")
                ).first()
                # Create flag if not present
                if not flag_b:
                    # Instantiate IntegrityFlag
                    flag_b = IntegrityFlag(
                        submission_id=sub_j.id,
                        flag_type="peer_similarity",
                        severity="high" if sim_score >= 85.0 else "medium",
                        description=f"Peer similarity score of {sim_score}% detected with {sub_a.student_name or 'Peer Student'}.",
                        details={"peer_submission_id": sub_a.id, "similarity_score": sim_score, "matched_phrases": matched_phrases},
                        status="new",
                    )
                    # Add flag to session
                    db.add(flag_b)
                    # Increment counter
                    flags_created += 1

    # Commit all created matches and flags
    db.commit()

    # Return scan summary
    return {
        "status": "completed",
        "assignment_id": assignment_id,
        "threshold": threshold,
        "pairs_evaluated": pairs_evaluated,
        "flags_created": flags_created,
    }
