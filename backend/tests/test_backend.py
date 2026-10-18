"""Unit and Integration Tests for Verism AI Backend Service."""

import pytest
from app.core.security import ferpa_cipher, verify_password, get_password_hash, create_access_token, decode_access_token
from app.services.ferpa_service import ferpa_service
from app.services.gemini_service import gemini_service
from app.services.vector_service import vector_service
from app.schemas.grading import StructuredGradingOutput


def test_ferpa_encryption_and_decryption():
    """Verify that student PII is safely encrypted and decrypted accurately."""
    original_name = "Rahul Sharma"
    encrypted = ferpa_cipher.encrypt(original_name)

    assert encrypted != original_name
    assert len(encrypted) > 10

    decrypted = ferpa_cipher.decrypt(encrypted)
    assert decrypted == original_name


def test_ferpa_pseudonymization_and_sanitization():
    """Verify that student PII is masked and pseudonymized for AI prompts."""
    sub_id = "sub_123"
    name = "Rahul Sharma"
    roll = "2024-047"
    email = "rahul.sharma@university.edu"
    raw_text = "Submitted by Rahul Sharma (2024-047, rahul.sharma@university.edu). Here is my graph algorithm implementation."

    pseudo_id, sanitized = ferpa_service.prepare_for_ai_evaluation(
        submission_id=sub_id,
        student_name=name,
        student_roll=roll,
        student_email=email,
        text_content=raw_text,
    )

    assert pseudo_id.startswith("STUDENT_")
    assert name not in sanitized
    assert roll not in sanitized
    assert email not in sanitized
    assert "[STUDENT_NAME]" in sanitized
    assert "[STUDENT_ROLL]" in sanitized
    assert "[STUDENT_EMAIL]" in sanitized


def test_password_hashing():
    """Verify password hashing and timing-safe verification."""
    password = "secret_password_123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_handling():
    """Verify JWT token creation and decoding."""
    token = create_access_token("inst_priya_rao")
    assert token is not None

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "inst_priya_rao"


def test_gemini_structured_fallback_evaluation():
    """Verify that rubric evaluation produces schema-compliant StructuredGradingOutput."""
    sample_text = "This report applies inheritance and polymorphism to model a banking transaction ledger."
    rubric_criteria = [
        {"name": "Understanding", "max_score": 30.0, "weight": 30.0},
        {"name": "Accuracy", "max_score": 30.0, "weight": 30.0},
        {"name": "Methodology", "max_score": 20.0, "weight": 20.0},
        {"name": "Presentation", "max_score": 20.0, "weight": 20.0},
    ]

    result = gemini_service.evaluate_submission(
        submission_text=sample_text,
        rubric_criteria=rubric_criteria,
        assignment_title="Assignment 3",
    )

    assert isinstance(result, StructuredGradingOutput)
    assert 0.0 <= result.overall_score <= 100.0
    assert len(result.criteria_evaluations) == 4
    assert result.feedback_summary is not None
    assert isinstance(result.ai_generated_probability, float)


def test_vector_similarity_and_matching_phrases():
    """Verify vector embedding generation and matching phrase detection."""
    text_a = "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes."
    text_b = "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type."

    matches = vector_service.find_matching_phrases(text_a, text_b, min_words=4)
    assert len(matches) > 0

    vec_a = vector_service.generate_embedding(text_a)
    assert len(vec_a) == vector_service.EMBEDDING_DIM


def test_supabase_client_and_service():
    """Verify Supabase client and SupabaseService PostgREST query layer."""
    from app.core.supabase import supabase
    from app.services.supabase_service import supabase_service

    assert supabase is not None
    assert supabase_service is not None

    courses = supabase_service.get_courses()
    assert isinstance(courses, list)
    assert len(courses) >= 4


def test_supabase_ferpa_submission_lifecycle():
    """Verify SupabaseService FERPA encryption and audit logging."""
    from app.services.supabase_service import supabase_service

    # Create submission with encrypted PII
    sub = supabase_service.create_submission(
        assignment_id="assign_oop_a3",
        student_name="Test Student",
        student_roll="2024-999",
        file_name="test_student_project.pdf",
        extracted_text="Testing tree and graph search algorithms.",
        student_email="test.student@university.edu",
    )
    assert sub is not None
    assert sub["id"].startswith("sub_")

    # Audit log entry
    audit = supabase_service.log_audit(
        actor_name="Dr. Priya Rao",
        action="TEST_ACTION",
        entity_type="Submission",
        entity_id=sub["id"],
        details={"test": True},
    )
    assert audit is not None
    assert audit["action"] == "TEST_ACTION"


def test_fastapi_health_endpoint():
    """Verify FastAPI /health endpoint returns accurate diagnostic status."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["supabase_configured"] is True
    assert data["ferpa_encryption"] == "active"
    assert data["qdrant_configured"] is True
    assert data["qdrant_mode"] in ("embedded/in-memory", "http://localhost:6333", ":memory:")


def test_user_signup_and_login_api():
    """Verify user signup and login endpoints work with Supabase/PostgreSQL sync."""
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    unique_email = f"prof_{uuid.uuid4().hex[:6]}@university.edu"

    # Test Sign Up
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Prof. Alan Turing",
            "email": unique_email,
            "password": "SecurePassword123!",
            "role": "Professor · Computer Science",
        },
    )
    assert signup_res.status_code == 201
    signup_data = signup_res.json()
    assert "access_token" in signup_data
    assert signup_data["user"]["email"] == unique_email
    token = signup_data["access_token"]

    # Test Get Current User /me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Prof. Alan Turing"

    # Test Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "SecurePassword123!",
        },
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_evaluation_with_reference_assignment_and_web_plagiarism():
    """Verify Gemini evaluator incorporates reference assignments and reports 3-way plagiarism metrics."""
    rubric = [
        {"name": "Correctness", "max_score": 50.0, "weight": 50.0, "description": "Correct algorithmic solution"},
        {"name": "Code Style", "max_score": 50.0, "weight": 50.0, "description": "Clean modular implementation"},
    ]
    reference = "def dijkstra(graph, start): heap = [(0, start)] ... optimal benchmark code"
    student_submission = "def dijkstra(g, s): q = [(0, s)] ... student solution"

    result = gemini_service.evaluate_submission(
        submission_text=student_submission,
        rubric_criteria=rubric,
        assignment_title="Dijkstra Shortest Path",
        reference_assignment_text=reference,
    )

    assert result.overall_score >= 0.0
    assert len(result.criteria_evaluations) == 2
    assert result.ai_generated_probability >= 0.0
    assert result.peer_to_peer_plagiarism_pct is not None
    assert result.web_plagiarism_pct is not None
    assert isinstance(result.web_sources, list)


