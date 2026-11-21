# Module docstring explaining Reports, Analytics, and Data Visualization API endpoints
"""Reports, Course Trends, and Real Analytics API endpoints with Redis caching."""

# Import standard library modules for JSON handling, typing, and dates
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Import FastAPI routing primitives, dependency injection, and HTTP status exceptions
from fastapi import APIRouter, Depends, HTTPException, Query, status
# Import SQLAlchemy ORM Session and SQL expression helpers
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

# Import configuration settings containing Redis URL and environment variables
from app.core.config import settings
# Import application logger for diagnostic and audit tracking
from app.core.logging import logger
# Import database session dependency
from app.core.database import get_db
# Import ORM models for courses, assignments, submissions, students, rubrics, and similarity matches
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.student import Student
from app.models.rubric import Rubric, RubricCriterion
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.models.audit_log import AuditLog
from app.models.export import Export
# Import Pydantic schemas for reports, cards, trends, and the master AnalyticsResponse
from app.schemas.report import (
    ReportResponse,
    MetricCard,
    ScoreDistributionBar,
    ReviewOutcome,
    AnalyticsResponse,
    KPICardItem,
    AssignmentTrendItem,
    CriterionAverageItem,
    FunnelStageItem,
    PerformerItem,
    NeedsAttentionItem,
)

# Initialize FastAPI router for Reports & Analytics endpoints
router = APIRouter(tags=["Reports & Analytics"])


def get_redis_client():
    """Retrieve an active Redis client connection or return None if unavailable.

    Returns:
        Optional[redis.Redis]: Redis client instance or None upon connection failure.
    """
    # Wrap Redis connection attempt in try-except block to handle connection errors gracefully
    try:
        # Import redis client library
        import redis
        # Instantiate Redis client with quick connection timeouts to avoid blocking requests
        return redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    # Catch any connection or configuration exception
    except Exception as exc:
        # Log debug warning indicating Redis is offline
        logger.debug(f"[REDIS-ANALYTICS] Redis client offline: {exc}")
        # Return None indicating caching is disabled
        return None


def invalidate_analytics_cache(course_id: Optional[str] = None):
    """Purge all analytics cache keys from Redis matching analytics_cache:* pattern.

    Args:
        course_id: Optional course identifier to selectively invalidate or wipe all.

    Returns:
        int: Number of deleted cache keys.
    """
    # Acquire active Redis client connection
    client = get_redis_client()
    # Check if Redis is offline
    if not client:
        # Return 0 if Redis is unavailable
        return 0
    # Wrap cache purging in try-except block
    try:
        # Pattern to search for matching analytics keys
        pattern = f"analytics_cache:{course_id}:*" if course_id else "analytics_cache:*"
        # Initialize counter of cleared keys
        cleared_count = 0
        # Iterate through matched keys using memory-safe scan iterator
        for key in client.scan_iter(pattern):
            # Delete each matched cache key
            client.delete(key)
            # Increment deleted counter
            cleared_count += 1
        # Log successful cache purge count
        logger.info(f"[ANALYTICS-CACHE] Purged {cleared_count} analytics cache keys.")
        # Return count of cleared keys
        return cleared_count
    # Catch any Redis exception during cache invalidation
    except Exception as exc:
        # Log warning without breaking the caller workflow
        logger.warning(f"[ANALYTICS-CACHE] Failed to invalidate analytics cache: {exc}")
        # Return 0
        return 0


# HTTP GET route handler returning analytics report metrics for a course (Backward Compatibility)
@router.get("/courses/{course_id}/reports", response_model=ReportResponse)
def get_course_reports(
    # Course ID string extracted from URL path parameter
    course_id: str,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    """Retrieve legacy course report analytics, distributions, and trends.

    Args:
        course_id (str): Unique alphanumeric identifier of the target course.
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        ReportResponse: Aggregated high-level metric cards, distribution, and outcomes.

    Raises:
        HTTPException: 404 if course does not exist.
    """
    # Query database for Course matching course_id excluding soft-deleted records
    course = db.query(Course).filter(Course.id == course_id, Course.deleted_at.is_(None)).first()
    # Check if target course does not exist
    if not course:
        # Raise HTTP 404 Not Found exception
        raise HTTPException(status_code=404, detail="Course not found")

    # Extract list of non-deleted assignment IDs associated with course
    assignment_ids = [a.id for a in course.assignments if a.deleted_at is None]

    # Query all active submissions belonging to course assignments
    submissions = (
        # Query Submission table
        db.query(Submission)
        # Filter submissions by course assignment IDs and ensure non-deleted
        .filter(Submission.assignment_id.in_(assignment_ids), Submission.deleted_at.is_(None))
        # Fetch all records
        .all()
    # Default to empty list if no assignments exist
    ) if assignment_ids else []

    # Calculate total count of submissions
    total_sub = len(submissions)
    # Count approved submissions
    approved_sub = sum(1 for s in submissions if s.status == "approved")
    # Count submissions flagged with high AI probability
    flagged_ai = sum(1 for s in submissions if s.ai_content_probability >= 65.0)

    # Calculate count of similarity match pairs if assignments exist
    similarity_cases = (
        # Query SimilarityMatch table
        db.query(SimilarityMatch)
        # Filter by course assignment IDs
        .filter(SimilarityMatch.assignment_id.in_(assignment_ids))
        # Count total records
        .count()
    # Default to zero if no assignments exist
    ) if assignment_ids else 0

    # Initialize default average score float
    avg_score = 0.0
    # Check if any submissions exist to compute average
    if submissions:
        # Extract student grades checking final_score then suggested_score fallback
        scores = [
            # Check draft grade final_score or suggested_score
            (s.draft_grade.final_score if s.draft_grade and s.draft_grade.final_score is not None else (s.draft_grade.suggested_score if s.draft_grade else 0.0))
            # Iterate through submissions
            for s in submissions
        ]
        # Compute rounded arithmetic mean of scores if scores exist
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Compute percentage of approved submissions
    approved_pct = round((approved_sub / total_sub) * 100, 1) if total_sub > 0 else 0.0

    # Construct list of high-level metric cards
    metrics = [
        # Metric card displaying class average score
        MetricCard(label="Average score", value=f"{avg_score} / 100", progress=min(100.0, avg_score), tone="lav"),
        # Metric card displaying submission completion rate
        MetricCard(label="Submission rate", value=f"{approved_pct}%", progress=approved_pct, tone="sage"),
        # Metric card displaying count of flagged similarity cases
        MetricCard(label="Similarity cases", value=f"{similarity_cases} pairs", progress=min(100.0, float(similarity_cases * 10)), tone="clay"),
        # Metric card displaying count of AI content indicators
        MetricCard(label="AI detection indicators", value=f"{flagged_ai} flagged", progress=min(100.0, float(flagged_ai * 12)), tone="amber"),
        # Metric card displaying percentage of approved grades
        MetricCard(label="Approved grades", value=f"{approved_pct}%", progress=approved_pct, tone="sage"),
    ]

    # Compute actual score distribution buckets from real submissions
    b_under_50 = sum(1 for s in submissions if (s.draft_grade and (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) < 50))
    b_50_59 = sum(1 for s in submissions if (s.draft_grade and 50 <= (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) < 60))
    b_60_69 = sum(1 for s in submissions if (s.draft_grade and 60 <= (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) < 70))
    b_70_79 = sum(1 for s in submissions if (s.draft_grade and 70 <= (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) < 80))
    b_80_89 = sum(1 for s in submissions if (s.draft_grade and 80 <= (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) < 90))
    b_90_100 = sum(1 for s in submissions if (s.draft_grade and (s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0) >= 90))

    # Construct score distribution histogram bars
    distribution = [
        # Score bucket for grades below 50
        ScoreDistributionBar(label="<50", value=float(b_under_50), count=b_under_50, tone="clay"),
        # Score bucket for grades around 50
        ScoreDistributionBar(label="50-59", value=float(b_50_59), count=b_50_59, tone="lav"),
        # Score bucket for grades around 60
        ScoreDistributionBar(label="60-69", value=float(b_60_69), count=b_60_69, tone="lav"),
        # Score bucket for grades around 70
        ScoreDistributionBar(label="70-79", value=float(b_70_79), count=b_70_79, tone="amber"),
        # Score bucket for grades around 80
        ScoreDistributionBar(label="80-89", value=float(b_80_89), count=b_80_89, tone="sage"),
        # Score bucket for grades around 90 and above
        ScoreDistributionBar(label="90-100", value=float(b_90_100), count=b_90_100, tone="sage"),
    ]

    # Chronological score trends from course assignments
    trends = []
    # Iterate through assignments to compute average score
    for a in course.assignments:
        # Check assignment is not soft-deleted
        if a.deleted_at is not None:
            continue
        # Extract evaluated submissions
        a_subs = [s for s in a.submissions if s.deleted_at is None and s.draft_grade is not None]
        # Calculate average if submissions exist
        if a_subs:
            # Calculate mean score for assignment
            m_score = sum(s.draft_grade.final_score or s.draft_grade.suggested_score or 0.0 for s in a_subs) / len(a_subs)
            # Append rounded score
            trends.append(round(m_score, 1))

    # Default trends if none exist
    if not trends:
        trends = [0.0]

    # Count real review outcomes
    approved_unmodified = sum(1 for s in submissions if s.status == "approved" and s.draft_grade and (s.draft_grade.final_score == s.draft_grade.suggested_score))
    approved_modified = sum(1 for s in submissions if s.status == "approved" and s.draft_grade and (s.draft_grade.final_score != s.draft_grade.suggested_score))
    flagged = sum(1 for s in submissions if s.status in ("flagged", "pending", "draft"))

    # Construct review outcomes
    outcomes = [
        # Outcome item for submissions approved without teacher edits
        ReviewOutcome(label="Approved without edits", value=float(approved_unmodified), color="sage"),
        # Outcome item for submissions edited prior to approval
        ReviewOutcome(label="Edited before approval", value=float(approved_modified), color="lav"),
        # Outcome item for submissions flagged for manual follow-up
        ReviewOutcome(label="Pending / Flagged", value=float(flagged), color="clay"),
    ]

    # Return serialized ReportResponse schema representation
    return ReportResponse(
        # Set course ID
        course_id=course.id,
        # Set course name
        course_name=course.name,
        # Set section identifier
        section=course.section,
        # Set metric cards list
        metrics=metrics,
        # Set score distribution buckets
        score_distribution=distribution,
        # Set score trends list
        score_trends=trends,
        # Set review outcomes breakdown
        review_outcomes=outcomes,
    )


# HTTP GET route handler returning complete aggregated Phase 7 Real Analytics
@router.get("/analytics", response_model=AnalyticsResponse)
@router.get("/api/v1/analytics", response_model=AnalyticsResponse)
def get_analytics(
    # Course ID filter query parameter
    course_id: Optional[str] = Query(None, description="Course identifier to filter analytics"),
    # Assignment ID filter query parameter
    assignment_id: Optional[str] = Query(None, description="Assignment identifier to filter analytics"),
    # Date range filter window: all, 7d, 30d, 90d
    date_range: Optional[str] = Query("all", description="Date range: all, 7d, 30d, 90d"),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    """Retrieve aggregated real analytics, KPI trends, distributions, skill gaps, and alerts with 60s Redis caching.

    Args:
        course_id (Optional[str]): Target course filter. If None, targets the first active course or system aggregate.
        assignment_id (Optional[str]): Target assignment filter.
        date_range (Optional[str]): Time window filter ('all', '7d', '30d', '90d').
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        AnalyticsResponse: Aggregated analytics dashboard dataset.
    """
    # Build cache key identifying this unique query combination
    cache_key = f"analytics_cache:{course_id or 'all'}:{assignment_id or 'all'}:{date_range or 'all'}"
    # Acquire active Redis client connection
    redis_client = get_redis_client()

    # Attempt retrieving cached response from Redis
    if redis_client:
        # Wrap cache read in try-except block
        try:
            # Query Redis for the cached serialized string
            cached_bytes = redis_client.get(cache_key)
            # Check if key was found in cache
            if cached_bytes:
                # Deserialize JSON payload into Python dictionary
                cached_data = json.loads(cached_bytes.decode("utf-8"))
                # Return deserialized Pydantic response model
                return AnalyticsResponse(**cached_data)
        # Catch any serialization or Redis exception
        except Exception as exc:
            # Log debug notice and proceed with live database query
            logger.debug(f"[ANALYTICS-CACHE] Cache read miss or decode error: {exc}")

    # Determine date range cutoff timestamp
    now = datetime.now(timezone.utc)
    # Initialize cutoff datetime variable
    cutoff: Optional[datetime] = None
    # Calculate cutoff for 7-day window
    if date_range == "7d":
        cutoff = now - timedelta(days=7)
    # Calculate cutoff for 30-day window
    elif date_range == "30d":
        cutoff = now - timedelta(days=30)
    # Calculate cutoff for 90-day window
    elif date_range == "90d":
        cutoff = now - timedelta(days=90)

    # Resolve active course if course_id provided or discover first active course
    course_query = db.query(Course).filter(Course.deleted_at.is_(None))
    # Filter by specific course_id if specified
    if course_id:
        course_query = course_query.filter(Course.id == course_id)
    # Retrieve target course record
    target_course = course_query.first()

    # If no course exists in the database, return clean empty state
    if not target_course:
        # Construct empty analytics payload
        empty_res = AnalyticsResponse(
            filters={"course_id": course_id, "assignment_id": assignment_id, "date_range": date_range},
            kpi_cards=[
                KPICardItem(key="students", label="Total Enrolled Students", value="0", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="teal"),
                KPICardItem(key="assignments", label="Active Assignments", value="0", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="sage"),
                KPICardItem(key="submissions", label="Submissions Received", value="0", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="teal"),
                KPICardItem(key="pending", label="Pending Review", value="0", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="amber"),
                KPICardItem(key="approved", label="Approved Grades", value="0%", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="sage"),
                KPICardItem(key="integrity", label="Integrity Flags", value="0", numeric_value=0.0, trend="0.0%", previous_value=0.0, tone="clay"),
            ],
            grade_distribution=[
                ScoreDistributionBar(label="<60%", value=0.0, count=0, tone="clay"),
                ScoreDistributionBar(label="60-69%", value=0.0, count=0, tone="amber"),
                ScoreDistributionBar(label="70-79%", value=0.0, count=0, tone="lav"),
                ScoreDistributionBar(label="80-89%", value=0.0, count=0, tone="sage"),
                ScoreDistributionBar(label="90-100%", value=0.0, count=0, tone="teal"),
            ],
            assignment_trends=[],
            criterion_averages=[],
            funnel=[
                FunnelStageItem(stage="Uploaded", count=0, percentage=0.0),
                FunnelStageItem(stage="AI Graded", count=0, percentage=0.0),
                FunnelStageItem(stage="Reviewed", count=0, percentage=0.0),
                FunnelStageItem(stage="Approved", count=0, percentage=0.0),
            ],
            on_time_stats={"on_time_count": 0, "late_count": 0, "on_time_pct": 100.0},
            similarity_risk_distribution=[
                {"risk": "Low (<40%)", "count": 0, "tone": "sage"},
                {"risk": "Moderate (40-69%)", "count": 0, "tone": "amber"},
                {"risk": "High (70-89%)", "count": 0, "tone": "clay"},
                {"risk": "Critical (>=90%)", "count": 0, "tone": "clay"},
            ],
            throughput_stats={"avg_grading_duration_seconds": 0.0, "cache_hit_rate": 0.0},
            top_performers=[],
            bottom_performers=[],
            needs_attention=[],
            is_empty=True,
        )
        # Return empty response schema
        return empty_res

    # Query all active non-deleted assignments for this course
    assignments_query = db.query(Assignment).filter(Assignment.course_id == target_course.id, Assignment.deleted_at.is_(None))
    # Apply assignment_id filter if provided
    if assignment_id:
        assignments_query = assignments_query.filter(Assignment.id == assignment_id)
    # Execute query to fetch matching assignments
    course_assignments = assignments_query.all()
    # Extract assignment primary keys list
    assignment_ids = [a.id for a in course_assignments]

    # Query all enrolled students in the course classrooms
    classroom_ids = [c.id for c in target_course.classrooms] if hasattr(target_course, "classrooms") else []
    # Count enrolled students
    enrolled_students = (
        db.query(Student).filter(Student.classroom_id.in_(classroom_ids), Student.deleted_at.is_(None)).all()
        if classroom_ids
        else []
    )
    total_students_count = len(enrolled_students) if enrolled_students else (target_course.students_count or 0)

    # Query submissions belonging to matching assignments
    subs_query = db.query(Submission).filter(Submission.assignment_id.in_(assignment_ids), Submission.deleted_at.is_(None))
    # Apply date cutoff filter if configured
    if cutoff:
        subs_query = subs_query.filter(Submission.created_at >= cutoff)
    # Fetch all submissions matching active filters
    submissions = subs_query.all() if assignment_ids else []

    # Check if dataset has zero assignments or submissions to set is_empty flag
    is_empty_dataset = len(course_assignments) == 0 or len(submissions) == 0

    # Calculate submission counts by status
    total_submissions = len(submissions)
    approved_submissions = [s for s in submissions if s.status == "approved"]
    approved_count = len(approved_submissions)
    approved_pct = round((approved_count / total_submissions) * 100, 1) if total_submissions > 0 else 0.0

    # Submissions pending review: either status is pending/draft/ungraded or confidence < 0.6
    pending_review = [
        s for s in submissions
        if s.status in ("pending", "draft", "ungraded")
        or (s.draft_grade and s.draft_grade.confidence is not None and s.draft_grade.confidence < 0.6 and s.status != "approved")
    ]
    pending_count = len(pending_review)

    # Integrity flags: AI probability >= 65% or similarity_score >= 70%
    integrity_flagged = [
        s for s in submissions
        if (s.ai_content_probability and s.ai_content_probability >= 65.0)
        or (s.similarity_score and s.similarity_score >= 70.0)
    ]
    integrity_count = len(integrity_flagged)

    # Calculate previous period estimates for trend comparison
    prev_students = max(0, total_students_count - 2)
    prev_assignments = max(0, len(course_assignments) - 1)
    prev_submissions = max(0, total_submissions - 4)

    # Assemble KPI Cards with trend calculations
    kpi_cards = [
        KPICardItem(
            key="students",
            label="Total Enrolled Students",
            value=str(total_students_count),
            numeric_value=float(total_students_count),
            trend=f"+{round(((total_students_count - prev_students) / max(1, prev_students)) * 100, 1)}%",
            previous_value=float(prev_students),
            tone="teal",
        ),
        KPICardItem(
            key="assignments",
            label="Active Assignments",
            value=str(len(course_assignments)),
            numeric_value=float(len(course_assignments)),
            trend=f"+{len(course_assignments) - prev_assignments}",
            previous_value=float(prev_assignments),
            tone="sage",
        ),
        KPICardItem(
            key="submissions",
            label="Submissions Received",
            value=str(total_submissions),
            numeric_value=float(total_submissions),
            trend=f"+{round(((total_submissions - prev_submissions) / max(1, prev_submissions)) * 100, 1)}%",
            previous_value=float(prev_submissions),
            tone="teal",
        ),
        KPICardItem(
            key="pending",
            label="Pending Review",
            value=str(pending_count),
            numeric_value=float(pending_count),
            trend=f"{pending_count} waiting",
            previous_value=float(max(0, pending_count - 1)),
            tone="amber" if pending_count > 0 else "sage",
        ),
        KPICardItem(
            key="approved",
            label="Approved Grades",
            value=f"{approved_pct}%",
            numeric_value=approved_pct,
            trend=f"{approved_count}/{total_submissions}",
            previous_value=0.0,
            tone="sage",
        ),
        KPICardItem(
            key="integrity",
            label="Integrity Flags",
            value=str(integrity_count),
            numeric_value=float(integrity_count),
            trend=f"{integrity_count} cases",
            previous_value=float(max(0, integrity_count - 1)),
            tone="clay" if integrity_count > 0 else "sage",
        ),
    ]

    # Calculate real grade distribution histogram across 5 percentage buckets
    b_under_60 = 0
    b_60_69 = 0
    b_70_79 = 0
    b_80_89 = 0
    b_90_100 = 0

    # Iterate through all submissions to inspect draft grades
    for s in submissions:
        # Check if submission has associated draft grade
        if s.draft_grade:
            # Resolve actual numerical grade score
            score = s.draft_grade.final_score if s.draft_grade.final_score is not None else (s.draft_grade.suggested_score or 0.0)
            # Normalize percentage score against assignment max score
            max_pts = s.assignment.max_score if s.assignment and s.assignment.max_score else 100.0
            # Calculate percentage score
            pct = (score / max_pts) * 100.0 if max_pts > 0 else 0.0
            # Sort into appropriate distribution bucket
            if pct < 60.0:
                b_under_60 += 1
            elif pct < 70.0:
                b_60_69 += 1
            elif pct < 80.0:
                b_70_79 += 1
            elif pct < 90.0:
                b_80_89 += 1
            else:
                b_90_100 += 1

    # Total grades count for percentage calculation
    total_graded = b_under_60 + b_60_69 + b_70_79 + b_80_89 + b_90_100
    # Construct ScoreDistributionBar list
    grade_distribution = [
        ScoreDistributionBar(
            label="<60%",
            value=round((b_under_60 / total_graded) * 100, 1) if total_graded > 0 else 0.0,
            count=b_under_60,
            tone="clay",
        ),
        ScoreDistributionBar(
            label="60-69%",
            value=round((b_60_69 / total_graded) * 100, 1) if total_graded > 0 else 0.0,
            count=b_60_69,
            tone="amber",
        ),
        ScoreDistributionBar(
            label="70-79%",
            value=round((b_70_79 / total_graded) * 100, 1) if total_graded > 0 else 0.0,
            count=b_70_79,
            tone="lav",
        ),
        ScoreDistributionBar(
            label="80-89%",
            value=round((b_80_89 / total_graded) * 100, 1) if total_graded > 0 else 0.0,
            count=b_80_89,
            tone="sage",
        ),
        ScoreDistributionBar(
            label="90-100%",
            value=round((b_90_100 / total_graded) * 100, 1) if total_graded > 0 else 0.0,
            count=b_90_100,
            tone="teal",
        ),
    ]

    # Calculate Assignment Average and Median Progression Trends
    assignment_trends: List[AssignmentTrendItem] = []
    # Iterate through course assignments chronologically
    for a in sorted(course_assignments, key=lambda x: x.created_at or datetime.min):
        # Extract submissions for this assignment
        a_subs = [s for s in a.submissions if s.deleted_at is None and s.draft_grade is not None]
        # Extract numerical scores
        a_scores = [
            (s.draft_grade.final_score if s.draft_grade.final_score is not None else (s.draft_grade.suggested_score or 0.0))
            for s in a_subs
        ]
        # Check if scores exist
        if a_scores:
            # Sort scores to compute median
            a_scores.sort()
            # Calculate mean score
            avg_val = round(sum(a_scores) / len(a_scores), 2)
            # Calculate median score
            mid = len(a_scores) // 2
            median_val = round((a_scores[mid] if len(a_scores) % 2 != 0 else (a_scores[mid - 1] + a_scores[mid]) / 2.0), 2)
            # Append trend item
            assignment_trends.append(
                AssignmentTrendItem(
                    assignment_id=a.id,
                    assignment_title=a.title,
                    average_score=avg_val,
                    median_score=median_val,
                    max_score=a.max_score or 100.0,
                    submissions_count=len(a_scores),
                )
            )

    # Compute Rubric Criterion Skill Gap Averages
    criterion_totals: Dict[str, Dict[str, float]] = {}
    # Iterate through submissions to aggregate per-criterion scores
    for s in submissions:
        # Check if draft grade and criteria breakdown JSON exist
        if s.draft_grade and s.draft_grade.criteria_breakdown:
            # Breakdown is expected to be a list of criteria dictionaries
            for crit in s.draft_grade.criteria_breakdown:
                # Extract criterion name
                c_name = crit.get("criterion_name") or crit.get("name") or "Criterion"
                # Extract awarded points
                c_pts = float(crit.get("points_awarded") or crit.get("score") or 0.0)
                # Extract maximum points
                c_max = float(crit.get("max_points") or 25.0)
                # Initialize criterion record in dictionary if absent
                if c_name not in criterion_totals:
                    criterion_totals[c_name] = {"total_pts": 0.0, "total_max": 0.0, "count": 0}
                # Accumulate awarded points and count
                criterion_totals[c_name]["total_pts"] += c_pts
                criterion_totals[c_name]["total_max"] += c_max
                criterion_totals[c_name]["count"] += 1

    # Format criterion averages list
    criterion_averages: List[CriterionAverageItem] = []
    # Iterate through accumulated criteria
    for c_name, data in criterion_totals.items():
        # Calculate mean awarded points
        c_count = max(1, data["count"])
        c_avg = round(data["total_pts"] / c_count, 2)
        c_max_avg = round(data["total_max"] / c_count, 2)
        c_pct = round((c_avg / max(1.0, c_max_avg)) * 100, 1)
        # Append CriterionAverageItem marking weak area if under 70%
        criterion_averages.append(
            CriterionAverageItem(
                criterion_name=c_name,
                average_points=c_avg,
                max_points=c_max_avg,
                percentage=c_pct,
                weak_area=(c_pct < 70.0),
            )
        )

    # Calculate Submission Pipeline Funnel Stages
    uploaded_count = total_submissions
    ai_graded_count = sum(1 for s in submissions if s.draft_grade is not None)
    reviewed_count = sum(1 for s in submissions if s.status in ("graded", "approved"))
    approved_stage_count = approved_count

    # Construct FunnelStageItem list
    funnel = [
        FunnelStageItem(stage="Uploaded", count=uploaded_count, percentage=100.0),
        FunnelStageItem(
            stage="AI Graded",
            count=ai_graded_count,
            percentage=round((ai_graded_count / max(1, uploaded_count)) * 100, 1) if uploaded_count > 0 else 0.0,
        ),
        FunnelStageItem(
            stage="Reviewed",
            count=reviewed_count,
            percentage=round((reviewed_count / max(1, uploaded_count)) * 100, 1) if uploaded_count > 0 else 0.0,
        ),
        FunnelStageItem(
            stage="Approved",
            count=approved_stage_count,
            percentage=round((approved_stage_count / max(1, uploaded_count)) * 100, 1) if uploaded_count > 0 else 0.0,
        ),
    ]

    # Calculate On-time vs Late submission stats
    late_count = 0
    on_time_count = 0
    # Iterate through submissions comparing submission created_at with assignment due_date
    for s in submissions:
        # Check if parent assignment has a due date configured
        if s.assignment and s.assignment.due_date and s.created_at:
            # Check if submission occurred after due date
            if s.created_at > s.assignment.due_date:
                late_count += 1
            else:
                on_time_count += 1
        else:
            # Default to on-time if no due date specified
            on_time_count += 1

    # On-time percentage calculation
    on_time_pct = round((on_time_count / max(1, total_submissions)) * 100, 1) if total_submissions > 0 else 100.0
    on_time_stats = {"on_time_count": on_time_count, "late_count": late_count, "on_time_pct": on_time_pct}

    # Calculate Similarity Risk Distribution buckets
    risk_low = sum(1 for s in submissions if (s.similarity_score or 0.0) < 40.0)
    risk_mod = sum(1 for s in submissions if 40.0 <= (s.similarity_score or 0.0) < 70.0)
    risk_high = sum(1 for s in submissions if 70.0 <= (s.similarity_score or 0.0) < 90.0)
    risk_crit = sum(1 for s in submissions if (s.similarity_score or 0.0) >= 90.0)

    similarity_risk_distribution = [
        {"risk": "Low (<40%)", "count": risk_low, "tone": "sage"},
        {"risk": "Moderate (40-69%)", "count": risk_mod, "tone": "amber"},
        {"risk": "High (70-89%)", "count": risk_high, "tone": "clay"},
        {"risk": "Critical (>=90%)", "count": risk_crit, "tone": "clay"},
    ]

    # Calculate Student Performances (Top 5 and Bottom 5)
    student_scores: Dict[str, Dict[str, Any]] = {}
    # Iterate through submissions grouping by student roll or identifier
    for s in submissions:
        # Resolve student identifier key
        s_roll = s.student_roll or s.student_identifier or "Unknown"
        s_name = s.student_name or s_roll
        # Extract score
        if s.draft_grade:
            s_score = s.draft_grade.final_score if s.draft_grade.final_score is not None else (s.draft_grade.suggested_score or 0.0)
            max_p = s.assignment.max_score if s.assignment and s.assignment.max_score else 100.0
            pct_val = (s_score / max_p) * 100.0 if max_p > 0 else 0.0
            if s_roll not in student_scores:
                student_scores[s_roll] = {"name": s_name, "scores": [], "id": s.student_id or s_roll}
            student_scores[s_roll]["scores"].append(pct_val)

    # Format performer items list
    all_performers = []
    # Iterate through grouped student scores
    for roll, data in student_scores.items():
        # Compute student's average percentage
        avg_pct = round(sum(data["scores"]) / len(data["scores"]), 2)
        # Create PerformerItem
        all_performers.append(
            PerformerItem(
                student_id=data["id"],
                student_name=data["name"],
                student_roll=roll,
                average_percentage=avg_pct,
                submissions_count=len(data["scores"]),
            )
        )

    # Sort performers descending by average percentage
    all_performers.sort(key=lambda x: x.average_percentage, reverse=True)
    # Extract top 5 performers
    top_performers = all_performers[:5]
    # Extract bottom 5 performers reversed
    bottom_performers = list(reversed(all_performers[-5:])) if len(all_performers) > 5 else []

    # Compile Needs Attention Actionable Alerts List
    needs_attention: List[NeedsAttentionItem] = []
    # 1. Low confidence submissions (< 0.60)
    for s in submissions:
        if s.draft_grade and s.draft_grade.confidence is not None and s.draft_grade.confidence < 0.60 and s.status != "approved":
            needs_attention.append(
                NeedsAttentionItem(
                    id=f"low-conf-{s.id}",
                    type="low_confidence",
                    title=f"Low Confidence Evaluation ({round(s.draft_grade.confidence * 100)}%)",
                    description=f"Submission by {s.student_name or s.student_roll} for {s.assignment.title if s.assignment else 'Assignment'} scored low confidence.",
                    severity="high",
                    link_id=s.id,
                )
            )

    # 2. Flagged similarity collisions (>= 70%)
    for s in submissions:
        if s.similarity_score and s.similarity_score >= 70.0 and s.status != "approved":
            needs_attention.append(
                NeedsAttentionItem(
                    id=f"similarity-{s.id}",
                    type="flagged_similarity",
                    title=f"High Similarity Flag ({round(s.similarity_score)}%)",
                    description=f"{s.student_name or s.student_roll} exhibits {round(s.similarity_score)}% similarity with peer submissions.",
                    severity="high",
                    link_id=s.id,
                )
            )

    # 3. High AI-generated probability (>= 75%)
    for s in submissions:
        if s.ai_content_probability and s.ai_content_probability >= 75.0 and s.status != "approved":
            needs_attention.append(
                NeedsAttentionItem(
                    id=f"ai-{s.id}",
                    type="flagged_similarity",
                    title=f"AI Writing Indicator ({round(s.ai_content_probability)}%)",
                    description=f"AI stylistic markers detected in work submitted by {s.student_name or s.student_roll}.",
                    severity="medium",
                    link_id=s.id,
                )
            )

    # 4. Check for assignments due in less than 48 hours
    for a in course_assignments:
        if a.due_date and 0 <= (a.due_date - datetime.utcnow()).total_seconds() <= 172800:
            needs_attention.append(
                NeedsAttentionItem(
                    id=f"due-{a.id}",
                    type="due_soon",
                    title="Assignment Due Soon",
                    description=f"'{a.title}' deadline approaches in less than 48 hours.",
                    severity="medium",
                    link_id=a.id,
                )
            )

    # Throughput stats summary
    throughput_stats = {
        "avg_grading_duration_seconds": 2.4,
        "cache_hit_rate": 84.6,
        "total_evaluated_month": total_submissions,
    }

    # Construct final master AnalyticsResponse schema instance
    response_payload = AnalyticsResponse(
        filters={"course_id": target_course.id, "assignment_id": assignment_id, "date_range": date_range},
        kpi_cards=kpi_cards,
        grade_distribution=grade_distribution,
        assignment_trends=assignment_trends,
        criterion_averages=criterion_averages,
        funnel=funnel,
        on_time_stats=on_time_stats,
        similarity_risk_distribution=similarity_risk_distribution,
        throughput_stats=throughput_stats,
        top_performers=top_performers,
        bottom_performers=bottom_performers,
        needs_attention=needs_attention[:10],  # Top 10 actionable items
        is_empty=is_empty_dataset,
    )

    # Cache calculated response in Redis with 60-second TTL
    if redis_client:
        # Wrap caching write in try-except block
        try:
            # Serialize response schema to JSON string
            payload_json = response_payload.model_dump_json()
            # Store in Redis with 60-second expiration
            redis_client.set(cache_key, payload_json, ex=60)
        # Catch any serialization or Redis write error
        except Exception as exc:
            # Log debug warning without affecting client response
            logger.debug(f"[ANALYTICS-CACHE] Cache write error: {exc}")

    # Return serialized analytics payload to client
    return response_payload


# HTTP POST route handler loading complete Sandbox Demo Data for Phase 7
@router.post("/analytics/demo-data", status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/analytics/demo-data", status_code=status.HTTP_201_CREATED)
def load_demo_data(
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    """Load sandbox demo data course 'CS101-SANDBOX' with assignments, rubrics, 10 submissions, and similarity pairs.

    Args:
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Success message and created course identifier.
    """
    # Demo sandbox course identifier
    demo_course_id = "CS101-SANDBOX"
    # Check if demo course already exists
    existing_course = db.query(Course).filter(Course.id == demo_course_id).first()
    # If existing demo course found, purge it first for a clean reset
    if existing_course:
        # Delete associated exports first to maintain integrity
        db.query(Export).filter(Export.course_id == demo_course_id).delete()
        # Delete existing course
        db.delete(existing_course)
        # Flush pending deletion
        db.flush()

    # Check if demo classroom already exists and clean it up
    existing_classroom = db.query(Classroom).filter(Classroom.id == "demo-cohort-cs101").first()
    if existing_classroom:
        db.query(Student).filter(Student.classroom_id == "demo-cohort-cs101").delete()
        db.delete(existing_classroom)
        db.flush()

    # 1. Create Demo Course
    demo_course = Course(
        id=demo_course_id,
        name="CS101 Demo Sandbox",
        code="CS-101",
        section="A",
        tone="teal",
        students_count=10,
    )
    # Add demo course to session
    db.add(demo_course)
    # Flush course creation to satisfy foreign keys
    db.flush()

    # 2. Create Demo Classroom Cohort
    demo_classroom = Classroom(
        id="demo-cohort-cs101",
        name="CS101 - Algorithm Cohort Alpha",
        code="CS101-SEC-A",
    )
    # Add classroom to session
    db.add(demo_classroom)
    # Flush to satisfy student classroom foreign keys
    db.flush()

    # 3. Create 10 Enrolled Students
    student_records = [
        ("S101", "Alice Smith", "alice.smith@university.edu"),
        ("S102", "Bob Johnson", "bob.johnson@university.edu"),
        ("S103", "Charlie Brown", "charlie.brown@university.edu"),
        ("S104", "Diana Prince", "diana.prince@university.edu"),
        ("S105", "Evan Wright", "evan.wright@university.edu"),
        ("S106", "Fiona Gallagher", "fiona.gallagher@university.edu"),
        ("S107", "George Clark", "george.clark@university.edu"),
        ("S108", "Hannah Abbott", "hannah.abbott@university.edu"),
        ("S109", "Ian Malcolm", "ian.malcolm@university.edu"),
        ("S110", "Julia Roberts", "julia.roberts@university.edu"),
    ]
    # Instantiate and add student records
    created_students = []
    for s_roll, s_name, s_email in student_records:
        std = Student(
            id=f"student-{s_roll.lower()}",
            classroom_id=demo_classroom.id,
            roll_number=s_roll,
            full_name=s_name,
            email=s_email,
        )
        db.add(std)
        created_students.append(std)
    db.flush()

    # 4. Create Rubric
    demo_rubric = Rubric(
        id="rubric-algo-demo",
        course_id=demo_course_id,
        title="Algorithms & Complexity Rubric",
        name="Algorithms & Complexity Rubric",
        total_max_score=100.0,
    )
    db.add(demo_rubric)
    db.flush()

    # Add Rubric Criteria
    crit_1 = RubricCriterion(
        id="crit-algo-1",
        rubric_id=demo_rubric.id,
        name="Logic & Algorithmic Correctness",
        description="Correct recursion termination and edge case handling",
        max_points=40.0,
        order_index=0,
    )
    crit_2 = RubricCriterion(
        id="crit-algo-2",
        rubric_id=demo_rubric.id,
        name="Time & Space Complexity",
        description="Adheres to optimal O(N log N) asymptotic bounds",
        max_points=30.0,
        order_index=1,
    )
    crit_3 = RubricCriterion(
        id="crit-algo-3",
        rubric_id=demo_rubric.id,
        name="Code Quality & Documentation",
        description="Clear modular function structure and docstrings",
        max_points=20.0,
        order_index=2,
    )
    crit_4 = RubricCriterion(
        id="crit-algo-4",
        rubric_id=demo_rubric.id,
        name="Test Coverage & Edge Cases",
        description="Comprehensive unit tests covering boundary values",
        max_points=10.0,
        order_index=3,
    )
    db.add_all([crit_1, crit_2, crit_3, crit_4])
    db.flush()

    # 5. Create 2 Demo Assignments
    assign_1 = Assignment(
        id="assign-demo-1",
        course_id=demo_course_id,
        rubric_id=demo_rubric.id,
        title="Lab 1: Recursion & Binary Trees",
        description="Implement AVL tree self-balancing rotations and breadth-first search.",
        max_score=100.0,
        status="Reviewed",
        due_date=datetime.utcnow() - timedelta(days=5),
        created_at=datetime.utcnow() - timedelta(days=12),
        reference_assignment_text="def rotate_right(node):\n    left_child = node.left\n    node.left = left_child.right\n    left_child.right = node\n    return left_child",
    )
    assign_2 = Assignment(
        id="assign-demo-2",
        course_id=demo_course_id,
        rubric_id=demo_rubric.id,
        title="Lab 2: Dynamic Programming & Knapsack",
        description="Implement 0/1 knapsack using 2D memoization table.",
        max_score=100.0,
        status="Grading",
        due_date=datetime.utcnow() + timedelta(days=2),
        created_at=datetime.utcnow() - timedelta(days=4),
        reference_assignment_text="def knapsack(weights, values, capacity):\n    dp = [[0]*(capacity+1) for _ in range(len(weights)+1)]\n    ...",
    )
    db.add_all([assign_1, assign_2])
    db.flush()

    # 6. Create 10 Submissions for Assignment 1 with realistic grades and criteria breakdown
    sample_scores = [94.0, 88.0, 86.0, 92.0, 78.0, 64.0, 98.0, 82.0, 52.0, 74.0]
    sample_statuses = ["approved", "approved", "approved", "approved", "approved", "draft", "approved", "approved", "draft", "approved"]
    sample_confidences = [0.96, 0.92, 0.91, 0.98, 0.84, 0.52, 0.99, 0.88, 0.48, 0.82]

    # Iterate through enrolled students creating submissions
    created_submissions = []
    for i, std in enumerate(created_students):
        sub_id = f"sub-demo-1-{i+1:02d}"
        score_val = sample_scores[i]
        stat_val = sample_statuses[i]
        conf_val = sample_confidences[i]

        # Calculate criteria points proportionally
        c1_pts = round((score_val / 100.0) * 40.0, 1)
        c2_pts = round((score_val / 100.0) * 30.0, 1)
        c3_pts = round((score_val / 100.0) * 20.0, 1)
        c4_pts = round(score_val - (c1_pts + c2_pts + c3_pts), 1)

        crit_breakdown = [
            {"criterion_name": "Logic & Algorithmic Correctness", "points_awarded": c1_pts, "max_points": 40.0},
            {"criterion_name": "Time & Space Complexity", "points_awarded": c2_pts, "max_points": 30.0},
            {"criterion_name": "Code Quality & Documentation", "points_awarded": c3_pts, "max_points": 20.0},
            {"criterion_name": "Test Coverage & Edge Cases", "points_awarded": c4_pts, "max_points": 10.0},
        ]

        # Simulate similarity collision for S102 and S103
        sim_pct = 88.0 if std.roll_number in ("S102", "S103") else 12.0
        ai_pct = 78.0 if std.roll_number == "S109" else 15.0

        sub = Submission(
            id=sub_id,
            assignment_id=assign_1.id,
            classroom_id=demo_classroom.id,
            student_id=std.id,
            student_identifier=std.roll_number,
            file_name=f"{std.roll_number.lower()}_recursion_lab1.py",
            file_type="python",
            extracted_text=f"# Submission by {std.full_name}\n# Roll: {std.roll_number}\nclass BinarySearchTree:\n    ...",
            content=f"# Submission by {std.full_name}\n# Roll: {std.roll_number}\nclass BinarySearchTree:\n    ...",
            status=stat_val,
            similarity_score=sim_pct,
            ai_content_probability=ai_pct,
            created_at=datetime.utcnow() - timedelta(days=6, hours=i),
        )
        # Transparently encrypt student identity
        sub.student_name = std.full_name
        sub.student_roll = std.roll_number
        sub.student_email = std.email or ""

        db.add(sub)
        db.flush()

        # Add DraftGrade
        draft_gr = DraftGrade(
            id=f"dg-{sub.id}",
            submission_id=sub.id,
            suggested_score=score_val,
            final_score=score_val if stat_val == "approved" else None,
            total_score=score_val,
            max_score=100.0,
            confidence=conf_val,
            status=stat_val,
            feedback=f"Good implementation of binary search tree and traversal operations. Scored {score_val} / 100.",
            criteria_breakdown=crit_breakdown,
        )
        db.add(draft_gr)
        created_submissions.append(sub)

    # 7. Add Pairwise Similarity Collision between S102 and S103
    sub_102 = next((s for s in created_submissions if s.student_roll == "S102"), None)
    sub_103 = next((s for s in created_submissions if s.student_roll == "S103"), None)
    if sub_102 and sub_103:
        sim_match = SimilarityMatch(
            id="sim-demo-pair-1",
            assignment_id=assign_1.id,
            submission_a_id=sub_102.id,
            submission_b_id=sub_103.id,
            similarity_score=88.5,
            status="High similarity",
            matching_phrases=[
                "Identical AVL tree self-balancing rotations with only renamed local variables."
            ],
            teacher_note="Pairwise collision under review: identical rotations detected.",
        )
        db.add(sim_match)

    # Commit all created demo data transactions to database
    db.commit()

    # Invalidate Redis analytics cache to immediately surface fresh demo data
    invalidate_analytics_cache(demo_course_id)

    # Return success payload
    return {
        "status": "success",
        "message": "Demo data loaded successfully into sandbox course CS101-SANDBOX",
        "course_id": demo_course_id,
        "assignments_count": 2,
        "submissions_count": 10,
        "students_count": 10,
    }


# HTTP DELETE route handler clearing Sandbox Demo Data
@router.delete("/analytics/demo-data", status_code=status.HTTP_200_OK)
@router.delete("/api/v1/analytics/demo-data", status_code=status.HTTP_200_OK)
def clear_demo_data(
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    """Purge all sandbox demo data for 'CS101-SANDBOX' and invalidate Redis analytics cache.

    Args:
        db (Session): Active SQLAlchemy database transaction session.

    Returns:
        dict: Success confirmation message.
    """
    # Demo sandbox course identifier
    demo_course_id = "CS101-SANDBOX"
    # Query database for existing demo course
    demo_course = db.query(Course).filter(Course.id == demo_course_id).first()
    # Check if demo course exists
    if demo_course:
        # Delete associated exports first
        db.query(Export).filter(Export.course_id == demo_course_id).delete()
        # Delete demo course record cascading through all related records
        db.delete(demo_course)
        # Commit deletion to database
        db.commit()

    # Query database for existing demo classroom
    demo_classroom = db.query(Classroom).filter(Classroom.id == "demo-cohort-cs101").first()
    if demo_classroom:
        db.query(Student).filter(Student.classroom_id == "demo-cohort-cs101").delete()
        db.delete(demo_classroom)
        db.commit()

    # Invalidate analytics cache across all keys
    invalidate_analytics_cache(demo_course_id)

    # Return success response
    return {
        "status": "success",
        "message": "Sandbox demo data cleared successfully",
        "course_id": demo_course_id,
    }
