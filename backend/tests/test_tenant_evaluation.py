"""Unit and Integration Tests for Multi-Tenant AI Assignment Evaluation Pipeline.

Validates:
1. Multi-tenant database models, schema, and unique constraint on (user_id, billing_month).
2. JWT Authentication and strict tenant isolation (User B cannot read/evaluate User A's folders).
3. Monthly usage and graceful quota exhaustion (HTTP 200, status='quota_deferred', NO 500 error).
4. Gemini evaluation structured output schema enforcement.
5. End-to-end evaluation trigger, persistence to EvaluationResult, and MonthlyUsage increment.
6. Error sanitization ensuring no raw database stack traces leak to the client.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.tenant_evaluation import (
    User,
    AssignmentFolder,
    Submission,
    EvaluationResult,
    MonthlyUsage,
)
from app.schemas.tenant_evaluation import EvaluationOutput
from app.services.quota_service import (
    check_and_increment_monthly_quota,
    get_or_create_monthly_usage,
    record_token_usage,
    get_current_billing_month,
)
from app.services.tenant_gemini_service import tenant_gemini_evaluator


@pytest.fixture
def test_client():
    """Provides a TestClient instance for testing endpoints."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Yields a database session and cleans up test data."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_mock_user(db, email_prefix="tenant"):
    """Helper to provision a test user and generate an access token."""
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    email = f"{email_prefix}_{uuid.uuid4().hex[:6]}@school.edu"
    user = User(
        id=user_id,
        email=email,
        name=f"Prof. {email_prefix.capitalize()}",
        full_name=f"Prof. {email_prefix.capitalize()}",
        role="Instructor",
        hashed_password=get_password_hash("Password123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return user, token


# ==============================================================================
# TEST 1: Database Schema & MonthlyUsage Unique Constraint
# ==============================================================================
def test_monthly_usage_unique_constraint(db_session):
    """Verifies UNIQUE(user_id, billing_month) constraint prevents duplicate monthly usage rows."""
    user, _ = create_mock_user(db_session, "quota_uniq")
    month = "2026-11"

    usage1 = MonthlyUsage(
        id=str(uuid.uuid4()),
        user_id=user.id,
        billing_month=month,
        submissions_evaluated=10,
        token_count=1500,
    )
    db_session.add(usage1)
    db_session.commit()

    # Attempting to add duplicate row for same user and month must fail with IntegrityError
    usage2 = MonthlyUsage(
        id=str(uuid.uuid4()),
        user_id=user.id,
        billing_month=month,
        submissions_evaluated=5,
        token_count=800,
    )
    db_session.add(usage2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ==============================================================================
# TEST 2: Strict Multi-Tenant Isolation
# ==============================================================================
def test_tenant_isolation_folder_access(test_client, db_session):
    """Verifies User B receives 404 when attempting to access or evaluate User A's folder."""
    user_a, token_a = create_mock_user(db_session, "tenant_a")
    user_b, token_b = create_mock_user(db_session, "tenant_b")

    # User A creates a folder
    create_res = test_client.post(
        "/api/v1/folders",
        json={
            "title": "Data Structures Project 1",
            "rubric_text": "Correctness: 50pts, Efficiency: 30pts, Documentation: 20pts",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_res.status_code == 201
    folder_a_id = create_res.json()["id"]

    # User A can access folder details
    user_a_res = test_client.get(
        f"/api/v1/folders/{folder_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert user_a_res.status_code == 200
    assert user_a_res.json()["title"] == "Data Structures Project 1"

    # User B attempting to view User A's folder must receive 404 (prevent ID enumeration)
    user_b_res = test_client.get(
        f"/api/v1/folders/{folder_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert user_b_res.status_code == 404
    assert "access denied" in user_b_res.json()["detail"].lower()

    # User B attempting to trigger evaluation on User A's folder must receive 404
    user_b_eval = test_client.post(
        f"/api/v1/folders/{folder_a_id}/evaluate",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert user_b_eval.status_code == 404
    assert "access denied" in user_b_eval.json()["detail"].lower()


# ==============================================================================
# TEST 3: Monthly Usage & Graceful Quota Exhaustion (No 500 error!)
# ==============================================================================
def test_monthly_quota_service_and_exhaustion(db_session):
    """Tests check_and_increment_monthly_quota service logic directly."""
    user, _ = create_mock_user(db_session, "quota_svc")
    month = get_current_billing_month()

    # Initial quota: 100 limit. Request 2 evals
    allowed, usage, remaining = check_and_increment_monthly_quota(
        db=db_session,
        user_id=user.id,
        count=2,
        max_quota=10,
    )
    assert allowed is True
    assert usage.submissions_evaluated == 2
    assert remaining == 8

    # Request 8 more -> reaches limit of 10
    allowed, usage, remaining = check_and_increment_monthly_quota(
        db=db_session,
        user_id=user.id,
        count=8,
        max_quota=10,
    )
    assert allowed is True
    assert usage.submissions_evaluated == 10
    assert remaining == 0

    # Request 1 more -> Quota exhausted, allowed must be False and counter must NOT increment
    allowed, usage, remaining = check_and_increment_monthly_quota(
        db=db_session,
        user_id=user.id,
        count=1,
        max_quota=10,
    )
    assert allowed is False
    assert usage.submissions_evaluated == 10
    assert remaining == 0


def test_quota_exhaustion_api_graceful_handling(test_client, db_session):
    """Verifies endpoint returns structured 200 with quota_deferred (NO unhandled 500!)."""
    user, token = create_mock_user(db_session, "quota_graceful")

    # Create folder
    create_res = test_client.post(
        "/api/v1/folders",
        json={
            "title": "Machine Learning Lab 3",
            "rubric_text": "Model Accuracy: 60%, Confusion Matrix: 40%",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    folder_id = create_res.json()["id"]

    # Add 2 student submissions
    for roll in ["CS-101", "CS-102"]:
        test_client.post(
            f"/api/v1/folders/{folder_id}/submissions",
            json={
                "student_identifier": roll,
                "extracted_text": f"import sklearn\n# Implementation for student {roll}\naccuracy = 0.94",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    # Artificially set user's monthly usage to the limit
    month = get_current_billing_month()
    usage = get_or_create_monthly_usage(db_session, user.id, month)
    usage.submissions_evaluated = 100  # Default quota limit reached
    db_session.commit()

    # Trigger evaluation: must return HTTP 200 with status 'quota_deferred'
    eval_res = test_client.post(
        f"/api/v1/folders/{folder_id}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["status"] == "quota_deferred"
    assert data["queued_submissions"] == 0
    assert data["deferred_submissions"] == 2
    assert "quota exhausted" in data["message"].lower()

    # Verify submissions in database transitioned to 'quota_deferred'
    subs = db_session.query(Submission).filter(Submission.folder_id == folder_id).all()
    for s in subs:
        assert s.evaluation_status == "quota_deferred"


# ==============================================================================
# TEST 4: Gemini Structured Output Schema
# ==============================================================================
@pytest.mark.anyio
async def test_gemini_evaluator_structured_output():
    """Verifies Gemini evaluation service returns schema matching score, breakdown, feedback, and improvement_areas."""
    rubric = "1. Code Correctness (50%): Solves the binary search problem.\n2. Complexity (50%): Runs in O(log N)."
    student_code = "def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n"

    result, tokens = await tenant_gemini_evaluator.evaluate_submission(
        rubric_text=rubric,
        extracted_text=student_code,
        student_identifier="STUDENT_BS_01",
    )

    assert isinstance(result, EvaluationOutput)
    assert 0.0 <= result.score <= 100.0
    assert isinstance(result.criteria_breakdown, dict)
    assert len(result.criteria_breakdown) > 0
    assert isinstance(result.feedback, str)
    assert len(result.feedback) > 5
    assert isinstance(result.improvement_areas, list)
    assert tokens >= 0


# ==============================================================================
# TEST 5: End-to-End Evaluation Flow & Persistence
# ==============================================================================
def test_evaluation_pipeline_e2e_persistence(test_client, db_session):
    """Tests end-to-end evaluation flow: folder creation, submission, evaluation, and DB persistence."""
    user, token = create_mock_user(db_session, "e2e_eval")

    # 1. Create folder
    create_res = test_client.post(
        "/api/v1/folders",
        json={
            "title": "Operating Systems - Synchronization",
            "rubric_text": "Deadlock prevention: 50%, Mutex usage: 50%",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    folder_id = create_res.json()["id"]

    # 2. Add 2 submissions
    sub1_res = test_client.post(
        f"/api/v1/folders/{folder_id}/submissions",
        json={
            "student_identifier": "OS-ROLL-01",
            "extracted_text": "pthread_mutex_lock(&lock);\nshared_resource++;\npthread_mutex_unlock(&lock);\n",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sub1_res.status_code == 201
    sub1_id = sub1_res.json()["id"]

    sub2_res = test_client.post(
        f"/api/v1/folders/{folder_id}/submissions",
        json={
            "student_identifier": "OS-ROLL-02",
            "extracted_text": "// Incomplete implementation with race condition\nshared_resource++;\n",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sub2_res.status_code == 201
    sub2_id = sub2_res.json()["id"]

    # 3. Trigger evaluation synchronously (sync=True)
    eval_res = test_client.post(
        f"/api/v1/folders/{folder_id}/evaluate?sync=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["status"] == "completed"
    assert eval_data["queued_submissions"] == 2

    # 4. Verify results persisted in EvaluationResult table
    res1 = db_session.query(EvaluationResult).filter(EvaluationResult.submission_id == sub1_id).first()
    assert res1 is not None
    assert 0.0 <= res1.score <= 100.0
    assert "feedback" in res1.feedback_json
    assert "criteria_breakdown" in res1.feedback_json

    res2 = db_session.query(EvaluationResult).filter(EvaluationResult.submission_id == sub2_id).first()
    assert res2 is not None
    assert 0.0 <= res2.score <= 100.0

    # 5. Verify MonthlyUsage counters updated
    usage = db_session.query(MonthlyUsage).filter(MonthlyUsage.user_id == user.id).first()
    assert usage is not None
    assert usage.submissions_evaluated == 2
    assert usage.token_count > 0

    # 6. Verify GET /folders/{folder_id} includes submissions with evaluation records
    folder_detail = test_client.get(
        f"/api/v1/folders/{folder_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert folder_detail.status_code == 200
    detail_data = folder_detail.json()
    assert detail_data["submission_count"] == 2
    assert len(detail_data["submissions"]) == 2
    for s in detail_data["submissions"]:
        assert s["evaluation_status"] == "completed"
        assert s["evaluation"] is not None
        assert s["evaluation"]["score"] >= 0.0


# ==============================================================================
# TEST 6: Error Sanitization
# ==============================================================================
def test_error_sanitization(test_client, db_session):
    """Verifies raw database traces or internal exceptions are never exposed to client responses."""
    user, token = create_mock_user(db_session, "sanitization")

    # Send invalid malformed folder payload
    res = test_client.post(
        "/api/v1/folders",
        json={"title": ""},  # rubric_text missing and title empty
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
    # Ensure no internal file paths or Python traceback syntax in response
    assert "Traceback" not in res.text
    assert "SELECT" not in res.text
    assert "psycopg2" not in res.text
