"""End-to-End User Flow Test Script.

Tests the complete single-teacher user journey:
1. Signup with unique teacher account
2. Login and JWT token issuance
3. Create course
4. Create assignment with criteria
5. Upload student submission
6. Trigger evaluation and draft grade generation
7. View report summary and verify data integrity
"""

# Import sys and os modules for environment configuration
import os
import sys
import uuid

# Ensure repository root and backend directory are in sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BACKEND_DIR = os.path.join(_REPO_ROOT, "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Import FastAPI TestClient
from fastapi.testclient import TestClient
# Import FastAPI application
from app.main import app
# Import database session factory
from app.core.database import SessionLocal
# Import ORM models for cleanup
from app.models.user import User
from app.models.course import Course
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade


def run_e2e_flow():
    """Executes the full user journey and validates each step."""
    # Initialize FastAPI TestClient
    client = TestClient(app)
    # Generate unique test user credentials
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"fresh_teacher_{unique_suffix}@verism.edu"
    password = f"SecureTeacherPass_{unique_suffix}!123"
    full_name = f"Prof. Fresh_{unique_suffix}"

    print(f"\n[1/7] Testing Teacher Signup for {email}...")
    # Step 1: Sign Up
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert signup_res.status_code in (200, 201), f"Signup failed: {signup_res.text}"
    signup_data = signup_res.json()
    token = signup_data.get("access_token")
    assert token, "No access token returned on signup"
    print("  -> Signup successful! JWT access token received.")

    # Step 2: Login
    print("\n[2/7] Testing Teacher Login...")
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("  -> Login verified successfully.")

    # Step 3: Create Course
    print("\n[3/7] Testing Course Creation...")
    course_res = client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "code": f"CS_{unique_suffix.upper()}",
            "name": "Advanced Operating Systems & Kernel Design",
            "section": "A",
            "tone": "lav",
        },
    )
    assert course_res.status_code in (200, 201), f"Course creation failed: {course_res.text}"
    course = course_res.json()
    course_id = course["id"]
    print(f"  -> Course created successfully: ID={course_id}, Code={course['code']}")

    # Step 4: Create Assignment
    print("\n[4/7] Testing Assignment Creation with Rubric...")
    assign_res = client.post(
        f"/api/v1/assignments?course_id={course_id}",
        headers=headers,
        json={
            "title": "Kernel Memory Allocation & Page Tables",
            "description": "Implement a two-level virtual page table in C.",
            "max_score": 100.0,
            "assignment_type": "coding",
            "similarity_threshold": 75.0,
            "starter_code": "// Provided kernel page table struct definition\ntypedef struct { uint32_t entries[1024]; } page_dir_t;",
            "rubric": [
                {
                    "name": "Page Table Allocation",
                    "max_score": 50.0,
                    "weight": 50.0,
                    "description": "Correct virtual to physical page mapping and fault recovery",
                },
                {
                    "name": "Memory Safety & Leaks",
                    "max_score": 50.0,
                    "weight": 50.0,
                    "description": "Clean deallocation without page leaking or buffer overflows",
                },
            ],
        },
    )
    assert assign_res.status_code in (200, 201), f"Assignment creation failed: {assign_res.text}"
    assignment = assign_res.json()
    assignment_id = assignment["id"]
    print(f"  -> Assignment created successfully: ID={assignment_id}")

    # Step 5: Upload Student Submission
    print("\n[5/7] Testing Student Submission Upload...")
    student_code = (
        "// Student implementation of virtual page table\n"
        "#include <stdint.h>\n"
        "int map_page(uint32_t virt, uint32_t phys) {\n"
        "    // Allocate page table entry cleanly\n"
        "    return 0;\n"
        "}\n"
    )
    upload_res = client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/upload",
        headers=headers,
        files={
            "file": ("student_submission.c", student_code.encode("utf-8"), "text/plain"),
        },
        data={
            "student_name": "Aarav Sharma",
            "roll_number": "CS26-104",
        },
    )
    assert upload_res.status_code in (200, 201), f"Upload failed: {upload_res.text}"
    submission = upload_res.json()
    submission_id = submission["id"]
    print(f"  -> Submission uploaded successfully: ID={submission_id}")

    # Step 6: Grade Submission
    print("\n[6/7] Testing AI Evaluation and Grade Stamping...")
    eval_res = client.post(
        f"/api/v1/submissions/{submission_id}/evaluate",
        headers=headers,
    )
    assert eval_res.status_code == 200, f"Evaluation failed: {eval_res.text}"
    eval_data = eval_res.json()
    suggested_score = eval_data.get("score")
    print(f"  -> AI Suggested Score: {suggested_score}/100, Status: {eval_data.get('status')}")

    # Stamp teacher grade approval
    stamp_res = client.put(
        f"/api/v1/submissions/{submission_id}/stamp-grade",
        headers=headers,
        json={
            "final_score": 92.5,
            "action": "APPROVE",
            "teacher_feedback": "Excellent implementation of page translation with clean comments.",
        },
    )
    assert stamp_res.status_code == 200, f"Grade stamp failed: {stamp_res.text}"
    print("  -> Grade stamped and approved by teacher: 92.5/100")

    # Step 7: View Analytics & Grade Distribution
    print("\n[7/7] Testing Analytics & Grade Distribution...")
    report_res = client.get(
        f"/api/v1/analytics?course_id={course_id}&assignment_id={assignment_id}",
        headers=headers,
    )
    assert report_res.status_code == 200, f"Report query failed: {report_res.text}"
    report_data = report_res.json()
    distribution = report_data.get("grade_distribution", [])
    print(f"  -> Grade distribution histogram buckets returned: {len(distribution)}")
    # Verify every distribution item has label and count without crashing startsWith
    for d in distribution:
        lbl = d.get("label", "")
        assert isinstance(lbl, str), f"Bucket label is not string: {lbl}"
        # Validate startsWith safety
        _ = lbl.startswith("90")
    print("  -> All distribution buckets safely validated with startsWith.")

    print("\n[SUCCESS] End-to-end fresh account user journey passed with zero errors!")

    # Cleanup test account and course
    db = SessionLocal()
    try:
        draft_record = db.query(DraftGrade).filter(DraftGrade.submission_id == submission_id).first()
        if draft_record:
            db.delete(draft_record)
        sub_record = db.query(Submission).filter(Submission.id == submission_id).first()
        if sub_record:
            db.delete(sub_record)
        assign_record = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if assign_record:
            db.delete(assign_record)
        course_record = db.query(Course).filter(Course.id == course_id).first()
        if course_record:
            db.delete(course_record)
        user_record = db.query(User).filter(User.email == email).first()
        if user_record:
            db.delete(user_record)
        db.commit()
        print("  -> Cleaned up test artifacts cleanly from database.")
    finally:
        db.close()


if __name__ == "__main__":
    run_e2e_flow()
