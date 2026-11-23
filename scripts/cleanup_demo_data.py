#!/usr/bin/env python3
"""Safe Database Demo & Test Data Cleanup Script for Verism AI.

Identifies and purges demo/seed fixtures and test records from PostgreSQL/Supabase
without touching user-created courses, assignments, or student submissions.

Usage:
    python scripts/cleanup_demo_data.py --dry-run
    python scripts/cleanup_demo_data.py --confirm
"""

# Import argparse for parsing command line arguments
import argparse
# Import os module for path operations
import os
# Import sys module for system path and exit controls
import sys
# Import typing primitives for structured return signatures
from typing import Dict, Any, List

# Ensure repository root and backend directory are present in sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Backend directory path
_BACKEND_DIR = os.path.join(_REPO_ROOT, "backend")
# Add backend directory to sys.path if missing
if _BACKEND_DIR not in sys.path:
    # Prepend backend directory
    sys.path.insert(0, _BACKEND_DIR)
# Add repo root to sys.path if missing
if _REPO_ROOT not in sys.path:
    # Prepend repo root
    sys.path.insert(0, _REPO_ROOT)

# Import SessionLocal database factory and engine
from app.core.database import SessionLocal, engine
# Import ORM models for relational traversal and cleanup
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.rubric import Rubric, RubricCriterion
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.models.export import Export
from app.models.user import User

# Define list of known demo/seed course identifiers
DEMO_COURSE_IDS = [
    # Sandbox demo course code
    "CS101-SANDBOX",
    # Default test course code
    "c_test_default",
]

# Define list of known demo classroom identifiers
DEMO_CLASSROOM_IDS = [
    # Sandbox demo cohort
    "demo-cohort-cs101",
]

# Define prefixes of ephemeral test classrooms
EPHEMERAL_CLASSROOM_PREFIXES = [
    # Deletion test classroom prefix
    "cls_del_",
]

# Define email patterns for test runner accounts
TEST_USER_EMAIL_PATTERNS = [
    # Ephemeral test accounts
    "@univ.edu",
    "@school.edu",
    "@verism.edu",
]


def scan_demo_records(db) -> Dict[str, Any]:
    """Scans the database for demo, test fixture, and seed records.

    Args:
        db: Active SQLAlchemy database session.

    Returns:
        Dict[str, Any]: Categorized record lists and counts identified for cleanup.
    """
    # Initialize results tracking dictionary
    results: Dict[str, Any] = {
        # Demo courses list
        "courses": [],
        # Demo classrooms list
        "classrooms": [],
        # Associated assignments list
        "assignments": [],
        # Associated submissions list
        "submissions": [],
        # Demo students list
        "students": [],
        # Associated exports list
        "exports": [],
    }

    # Query all courses
    all_courses = db.query(Course).all()
    # Iterate through courses
    for course in all_courses:
        # Check if course matches demo criteria
        is_demo = (
            course.id in DEMO_COURSE_IDS
            or course.code in DEMO_COURSE_IDS
            or (course.id and any(course.id.startswith(p) for p in EPHEMERAL_CLASSROOM_PREFIXES))
            or course.instructor_id == "inst_priya_rao"
            or course.user_id == "inst_priya_rao"
        )
        # If demo course matched, record it
        if is_demo:
            # Append course record summary
            results["courses"].append({
                "id": course.id,
                "code": course.code,
                "name": course.name,
            })

    # Collect identified course IDs
    matched_course_ids = [c["id"] for c in results["courses"]]

    # Query classrooms matching demo IDs or prefixes
    all_classrooms = db.query(Classroom).all()
    # Iterate through classrooms
    for classroom in all_classrooms:
        # Check if classroom matches demo criteria
        if classroom.id in DEMO_CLASSROOM_IDS or any(classroom.id.startswith(p) for p in EPHEMERAL_CLASSROOM_PREFIXES):
            # Append classroom record summary
            results["classrooms"].append({
                "id": classroom.id,
                "name": classroom.name,
            })

    # Query assignments associated with matched demo courses
    if matched_course_ids:
        # Filter assignments by course IDs
        matched_assignments = db.query(Assignment).filter(Assignment.course_id.in_(matched_course_ids)).all()
        # Iterate through assignments
        for a in matched_assignments:
            # Append assignment summary
            results["assignments"].append({
                "id": a.id,
                "title": a.title,
                "course_id": a.course_id,
            })

    # Collect matched assignment IDs
    matched_assignment_ids = [a["id"] for a in results["assignments"]]

    # Query submissions associated with matched assignments
    if matched_assignment_ids:
        # Filter submissions
        matched_submissions = db.query(Submission).filter(Submission.assignment_id.in_(matched_assignment_ids)).all()
        # Iterate through submissions
        for s in matched_submissions:
            # Append submission summary
            results["submissions"].append({
                "id": s.id,
                "assignment_id": s.assignment_id,
            })

    # Return scan summary
    return results


def purge_demo_records(db, scan_results: Dict[str, Any]) -> int:
    """Safely executes the transactional deletion of identified demo records.

    Args:
        db: Active SQLAlchemy database session.
        scan_results (Dict[str, Any]): Pre-computed record scan from scan_demo_records.

    Returns:
        int: Total number of entities deleted.
    """
    # Track count of deleted records
    deleted_count = 0

    # Extract identifiers
    course_ids = [c["id"] for c in scan_results["courses"]]
    classroom_ids = [c["id"] for c in scan_results["classrooms"]]
    assignment_ids = [a["id"] for a in scan_results["assignments"]]
    submission_ids = [s["id"] for s in scan_results["submissions"]]

    # Delete exports targeting demo courses
    if course_ids:
        # Execute deletion
        exp_del = db.query(Export).filter(Export.course_id.in_(course_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += exp_del

    # Delete similarity matches associated with demo submissions
    if submission_ids:
        # Delete source matches
        sim_del_1 = db.query(SimilarityMatch).filter(SimilarityMatch.submission_a_id.in_(submission_ids)).delete(synchronize_session=False)
        # Delete target matches
        sim_del_2 = db.query(SimilarityMatch).filter(SimilarityMatch.submission_b_id.in_(submission_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += (sim_del_1 + sim_del_2)

        # Delete draft grades associated with demo submissions
        dg_del = db.query(DraftGrade).filter(DraftGrade.submission_id.in_(submission_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += dg_del

        # Delete submissions
        sub_del = db.query(Submission).filter(Submission.id.in_(submission_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += sub_del

    # Delete assignments
    if assignment_ids:
        # Execute deletion
        assign_del = db.query(Assignment).filter(Assignment.id.in_(assignment_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += assign_del

    # Delete classrooms and enrolled students
    if classroom_ids:
        # Delete students
        st_del = db.query(Student).filter(Student.classroom_id.in_(classroom_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += st_del
        # Delete classrooms
        cls_del = db.query(Classroom).filter(Classroom.id.in_(classroom_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += cls_del

    # Delete courses
    if course_ids:
        # Execute deletion
        course_del = db.query(Course).filter(Course.id.in_(course_ids)).delete(synchronize_session=False)
        # Increment counter
        deleted_count += course_del

    # Commit transaction to PostgreSQL
    db.commit()

    # Return total deleted count
    return deleted_count


def main():
    """Main CLI execution entry point."""
    # Initialize argument parser
    parser = argparse.ArgumentParser(
        description="Safe Demo & Test Data Cleanup for Verism AI"
    )
    # Add dry-run flag
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and display demo records without modifying database",
    )
    # Add confirm flag
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Execute the permanent deletion of identified demo data",
    )

    # Parse command line arguments
    args = parser.parse_args()

    # Enforce safe default: require explicit flag
    if not args.dry_run and not args.confirm:
        # Print guidance
        print("Please specify --dry-run to preview or --confirm to execute cleanup.")
        # Exit with error code
        sys.exit(1)

    # Establish database session
    db = SessionLocal()
    # Open try-finally block for session lifecycle management
    try:
        # Execute demo scan
        print("\nScanning database for demo, test fixture, and seed records...")
        # Get scan results
        scan = scan_demo_records(db)

        # Print scan findings
        print(f"\nFound {len(scan['courses'])} demo course(s):")
        # List courses
        for c in scan["courses"]:
            # Print course details
            print(f"  - Course [{c['id']}] {c['code']} - {c['name']}")

        # Print classrooms
        print(f"\nFound {len(scan['classrooms'])} demo classroom(s):")
        # List classrooms
        for cl in scan["classrooms"]:
            # Print classroom details
            print(f"  - Classroom [{cl['id']}] {cl['name']}")

        # Print assignments
        print(f"\nFound {len(scan['assignments'])} associated assignment(s)")
        # Print submissions
        print(f"Found {len(scan['submissions'])} associated submission(s)")

        # Handle dry run mode
        if args.dry_run:
            # Print notice
            print("\n[DRY RUN] No records were modified or deleted.")
            # Exit clean
            return

        # Handle confirmation mode
        if args.confirm:
            # Prompt user for final confirmation if interactive
            print("\nProceeding with permanent deletion of demo records...")
            # Execute cleanup
            total_deleted = purge_demo_records(db, scan)
            # Print success confirmation
            print(f"\n[SUCCESS] Successfully purged {total_deleted} demo and fixture records from database.")

    # Handle operational exceptions
    except Exception as exc:
        # Rollback active transaction
        db.rollback()
        # Print error details
        print(f"\n[ERROR] Database cleanup encountered an error: {exc}")
        # Re-raise for traceback
        raise
    # Finally block closing session
    finally:
        # Close database session
        db.close()


# Standard Python script execution guard
if __name__ == "__main__":
    # Execute main entry point
    main()
