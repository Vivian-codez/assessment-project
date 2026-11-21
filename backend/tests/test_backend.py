# Docstring explaining Unit and Integration Tests for Verism AI Backend Service.
"""Unit and Integration Tests for Verism AI Backend Service."""

# Import module pytest
import pytest
# Import ferpa_cipher, verify_password, get_password_hash, create_access_token, decode_access_token from app.core.security
from app.core.security import ferpa_cipher, verify_password, get_password_hash, create_access_token, decode_access_token
# Import ferpa_service from app.services.ferpa_service
from app.services.ferpa_service import ferpa_service
# Import gemini_service from app.services.gemini_service
from app.services.gemini_service import gemini_service
# Import vector_service from app.services.vector_service
from app.services.vector_service import vector_service
# Import StructuredGradingOutput from app.schemas.grading
from app.schemas.grading import StructuredGradingOutput


# Define function test_ferpa_encryption_and_decryption
def test_ferpa_encryption_and_decryption():
    # Docstring explaining Verify that student PII is safely encrypted and decrypted ac
    """Verify that student PII is safely encrypted and decrypted accurately."""
    # Set original_name to "Rahul Sharma"
    original_name = "Rahul Sharma"
    # Set encrypted to ferpa_cipher.encrypt(original_name)
    encrypted = ferpa_cipher.encrypt(original_name)

    # Assert condition: encrypted != original_name
    assert encrypted != original_name
    # Assert condition: len(encrypted) > 10
    assert len(encrypted) > 10

    # Set decrypted to ferpa_cipher.decrypt(encrypted)
    decrypted = ferpa_cipher.decrypt(encrypted)
    # Assert condition: decrypted == original_name
    assert decrypted == original_name


# Define function test_ferpa_pseudonymization_and_sanitization
def test_ferpa_pseudonymization_and_sanitization():
    # Docstring explaining Verify that student PII is masked and pseudonymized for AI p
    """Verify that student PII is masked and pseudonymized for AI prompts."""
    # Set sub_id to "sub_123"
    sub_id = "sub_123"
    # Set name to "Rahul Sharma"
    name = "Rahul Sharma"
    # Set roll to "2024-047"
    roll = "2024-047"
    # Set email to "rahul.sharma@university.edu"
    email = "rahul.sharma@university.edu"
    # Set raw_text to "Submitted by Rahul Sharma (2024-047, rahul.sharma@university.edu). Here is my graph algorithm implementation."
    raw_text = "Submitted by Rahul Sharma (2024-047, rahul.sharma@university.edu). Here is my graph algorithm implementation."

    # Set pseudo_id, sanitized to ferpa_service.prepare_for_ai_evaluation(
    pseudo_id, sanitized = ferpa_service.prepare_for_ai_evaluation(
        # Specify argument: submission_id=sub_id
        submission_id=sub_id,
        # Specify argument: student_name=name
        student_name=name,
        # Specify argument: student_roll=roll
        student_roll=roll,
        # Specify argument: student_email=email
        student_email=email,
        # Specify argument: text_content=raw_text
        text_content=raw_text,
    )

    # Assert condition: pseudo_id.startswith("STUDENT_")
    assert pseudo_id.startswith("STUDENT_")
    # Assert condition: name not in sanitized
    assert name not in sanitized
    # Assert condition: roll not in sanitized
    assert roll not in sanitized
    # Assert condition: email not in sanitized
    assert email not in sanitized
    # Assert condition: "[STUDENT_NAME]" in sanitized
    assert "[STUDENT_NAME]" in sanitized
    # Assert condition: "[STUDENT_ROLL]" in sanitized
    assert "[STUDENT_ROLL]" in sanitized
    # Assert condition: "[STUDENT_EMAIL]" in sanitized
    assert "[STUDENT_EMAIL]" in sanitized


# Define function test_password_hashing
def test_password_hashing():
    # Docstring explaining Verify password hashing and timing-safe verification.
    """Verify password hashing and timing-safe verification."""
    # Set password to "secret_password_123"
    password = "secret_password_123"
    # Set hashed to get_password_hash(password)
    hashed = get_password_hash(password)

    # Assert condition: hashed != password
    assert hashed != password
    # Assert condition: verify_password(password, hashed) is True
    assert verify_password(password, hashed) is True
    # Assert condition: verify_password("wrong_password", hashed) is False
    assert verify_password("wrong_password", hashed) is False


# Define function test_jwt_token_handling
def test_jwt_token_handling():
    # Docstring explaining Verify JWT token creation and decoding.
    """Verify JWT token creation and decoding."""
    # Set token to create_access_token("inst_priya_rao")
    token = create_access_token("inst_priya_rao")
    # Assert condition: token is not None
    assert token is not None

    # Set decoded to decode_access_token(token)
    decoded = decode_access_token(token)
    # Assert condition: decoded is not None
    assert decoded is not None
    # Assert condition: decoded.get("sub") == "inst_priya_rao"
    assert decoded.get("sub") == "inst_priya_rao"


# Define function test_gemini_structured_fallback_evaluation
def test_gemini_structured_fallback_evaluation():
    # Docstring explaining Verify that rubric evaluation produces schema-compliant Stru
    """Verify that rubric evaluation produces schema-compliant StructuredGradingOutput."""
    # Set sample_text to "This report applies inheritance and polymorphism to model a banking transaction ledger."
    sample_text = "This report applies inheritance and polymorphism to model a banking transaction ledger."
    # Set rubric_criteria to [
    rubric_criteria = [
        # Define field entry: {"name": "Understanding", "max_score": 30.0, "weight": 30.0}
        {"name": "Understanding", "max_score": 30.0, "weight": 30.0},
        # Define field entry: {"name": "Accuracy", "max_score": 30.0, "weight": 30.0}
        {"name": "Accuracy", "max_score": 30.0, "weight": 30.0},
        # Define field entry: {"name": "Methodology", "max_score": 20.0, "weight": 20.0}
        {"name": "Methodology", "max_score": 20.0, "weight": 20.0},
        # Define field entry: {"name": "Presentation", "max_score": 20.0, "weight": 20.0}
        {"name": "Presentation", "max_score": 20.0, "weight": 20.0},
    ]

    # Set result to gemini_service.evaluate_submission(
    result = gemini_service.evaluate_submission(
        # Specify argument: submission_text=sample_text
        submission_text=sample_text,
        # Specify argument: rubric_criteria=rubric_criteria
        rubric_criteria=rubric_criteria,
        # Specify argument: assignment_title="Assignment 3"
        assignment_title="Assignment 3",
    )

    # Assert condition: isinstance(result, StructuredGradingOutput)
    assert isinstance(result, StructuredGradingOutput)
    # Assert condition: 0.0 <= result.overall_score <= 100.0
    assert 0.0 <= result.overall_score <= 100.0
    # Assert condition: len(result.criteria_evaluations) == 4
    assert len(result.criteria_evaluations) == 4
    # Assert condition: result.feedback_summary is not None
    assert result.feedback_summary is not None
    # Assert condition: isinstance(result.ai_generated_probability, float)
    assert isinstance(result.ai_generated_probability, float)


# Define function test_vector_similarity_and_matching_phrases
def test_vector_similarity_and_matching_phrases():
    # Docstring explaining Verify vector embedding generation and matching phrase detec
    """Verify vector embedding generation and matching phrase detection."""
    # Set text_a to "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes."
    text_a = "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes."
    # Set text_b to "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type."
    text_b = "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type."

    # Set matches to vector_service.find_matching_phrases(text_a, text_b, min_words=4)
    matches = vector_service.find_matching_phrases(text_a, text_b, min_words=4)
    # Assert condition: len(matches) > 0
    assert len(matches) > 0

    # Set vec_a to vector_service.generate_embedding(text_a)
    vec_a = vector_service.generate_embedding(text_a)
    # Assert condition: len(vec_a) == vector_service.EMBEDDING_DIM
    assert len(vec_a) == vector_service.EMBEDDING_DIM


# Define function test_supabase_client_and_service
def test_supabase_client_and_service():
    # Docstring explaining Verify Supabase client and SupabaseService PostgREST query l
    """Verify Supabase client and SupabaseService PostgREST query layer."""
    # Import supabase from app.core.supabase
    from app.core.supabase import supabase
    # Import supabase_service from app.services.supabase_service
    from app.services.supabase_service import supabase_service

    # Assert condition: supabase is not None
    assert supabase is not None
    # Assert condition: supabase_service is not None
    assert supabase_service is not None

    # Set courses to supabase_service.get_courses()
    courses = supabase_service.get_courses()
    # Assert condition: isinstance(courses, list)
    assert isinstance(courses, list)
    # Assert condition: len(courses) >= 1
    assert len(courses) >= 1


# Define function test_supabase_ferpa_submission_lifecycle
def test_supabase_ferpa_submission_lifecycle():
    # Docstring explaining Verify SupabaseService FERPA encryption and audit logging.
    """Verify SupabaseService FERPA encryption and audit logging."""
    # Import supabase_service from app.services.supabase_service
    from app.services.supabase_service import supabase_service

    # Create submission with encrypted PII
    sub = supabase_service.create_submission(
        # Specify argument: assignment_id="assign_oop_a3"
        assignment_id="assign_oop_a3",
        # Specify argument: student_name="Test Student"
        student_name="Test Student",
        # Specify argument: student_roll="2024-999"
        student_roll="2024-999",
        # Specify argument: file_name="test_student_project.pdf"
        file_name="test_student_project.pdf",
        # Specify argument: extracted_text="Testing tree and graph search algorithms."
        extracted_text="Testing tree and graph search algorithms.",
        # Specify argument: student_email="test.student@university.edu"
        student_email="test.student@university.edu",
    )
    # Assert condition: sub is not None
    assert sub is not None
    # Assert condition: sub["id"].startswith("sub_")
    assert sub["id"].startswith("sub_")

    # Audit log entry
    audit = supabase_service.log_audit(
        # Specify argument: actor_name="Dr. Priya Rao"
        actor_name="Dr. Priya Rao",
        # Specify argument: action="TEST_ACTION"
        action="TEST_ACTION",
        # Specify argument: entity_type="Submission"
        entity_type="Submission",
        # Specify argument: entity_id=sub["id"]
        entity_id=sub["id"],
        # Specify argument: details={"test": True}
        details={"test": True},
    )
    # Assert condition: audit is not None
    assert audit is not None
    # Assert condition: audit["action"] == "TEST_ACTION"
    assert audit["action"] == "TEST_ACTION"


# Define function test_fastapi_health_endpoint
def test_fastapi_health_endpoint():
    # Docstring explaining Verify FastAPI /health endpoint returns accurate diagnostic 
    """Verify FastAPI /health endpoint returns accurate diagnostic status."""
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set response to client.get("/health")
    response = client.get("/health")
    # Assert condition: response.status_code == 200
    assert response.status_code == 200
    # Set data to response.json()
    data = response.json()
    # Assert condition: data["status"] == "healthy"
    assert data["status"] == "healthy"
    # Assert condition: data["supabase_configured"] is True
    assert data["supabase_configured"] is True
    # Assert condition: data["ferpa_encryption"] == "active"
    assert data["ferpa_encryption"] == "active"
    # Assert condition: data["qdrant_configured"] is True
    assert data["qdrant_configured"] is True
    # Assert condition: data["qdrant_mode"] in ("embedded/in-memory", "http://localhost:6333", ":memory:")
    assert data["qdrant_mode"] in ("embedded/in-memory", "http://localhost:6333", ":memory:")


# Define function test_user_signup_and_login_api
def test_user_signup_and_login_api():
    # Docstring explaining Verify user signup, OAuth2 login, and /auth/me endpoints wor
    """Verify user signup, OAuth2 login, and /auth/me endpoints work with PostgreSQL and JWT."""
    # Import module uuid
    import uuid
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app
    # Import SessionLocal from app.core.database
    from app.core.database import SessionLocal
    # Import User from app.models.user
    from app.models.user import User

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set unique_email to f"prof_{uuid.uuid4().hex[:6]}@university.edu"
    unique_email = f"prof_{uuid.uuid4().hex[:6]}@university.edu"

    # 1. Test Sign Up with full_name payload
    signup_res = client.post(
        # Execute statement: "/api/v1/auth/signup",
        "/api/v1/auth/signup",
        # Execute statement: json={
        json={
            # Define field entry: "full_name": "Prof. Alan Turing"
            "full_name": "Prof. Alan Turing",
            # Define field entry: "email": unique_email
            "email": unique_email,
            # Define field entry: "password": "SecurePassword123!"
            "password": "SecurePassword123!",
            # Define field entry: "role": "Professor · Computer Science"
            "role": "Professor · Computer Science",
        },
    )
    # Assert condition: signup_res.status_code == 201
    assert signup_res.status_code == 201
    # Set signup_data to signup_res.json()
    signup_data = signup_res.json()
    # Assert condition: "access_token" in signup_data
    assert "access_token" in signup_data
    # Assert condition: signup_data["token_type"] == "bearer"
    assert signup_data["token_type"] == "bearer"
    # Set user_obj to signup_data["user"]
    user_obj = signup_data["user"]
    # Assert condition: user_obj["email"] == unique_email
    assert user_obj["email"] == unique_email
    # Assert condition: user_obj["full_name"] == "Prof. Alan Turing"
    assert user_obj["full_name"] == "Prof. Alan Turing"
    # Assert condition: user_obj["role"] == "Professor · Computer Science"
    assert user_obj["role"] == "Professor · Computer Science"
    # Assert condition: "id" in user_obj
    assert "id" in user_obj
    # Set token to signup_data["access_token"]
    token = signup_data["access_token"]

    # Verify password was hashed with bcrypt in PostgreSQL
    db = SessionLocal()
    # Begin try block to handle operations safely
    try:
        # Set stored_user to db.query(User).filter(User.email == unique_email).first()
        stored_user = db.query(User).filter(User.email == unique_email).first()
        # Assert condition: stored_user is not None
        assert stored_user is not None
        # Assert condition: stored_user.hashed_password.startswith("$2")
        assert stored_user.hashed_password.startswith("$2")
        # Assert condition: "SecurePassword123!" not in stored_user.hashed_password
        assert "SecurePassword123!" not in stored_user.hashed_password
    # Execute cleanup block in finally clause
    finally:
        # Execute statement: db.close()
        db.close()

    # 2. Test duplicate email registration raises HTTP 400
    dup_res = client.post(
        # Execute statement: "/api/v1/auth/signup",
        "/api/v1/auth/signup",
        # Execute statement: json={
        json={
            # Define field entry: "full_name": "Duplicate Turing"
            "full_name": "Duplicate Turing",
            # Define field entry: "email": unique_email
            "email": unique_email,
            # Define field entry: "password": "AnotherPassword456!"
            "password": "AnotherPassword456!",
        },
    )
    # Assert condition: dup_res.status_code == 400
    assert dup_res.status_code == 400
    # Assert condition: "already exists" in dup_res.json()["detail"]
    assert "already exists" in dup_res.json()["detail"]

    # 3. Test Get Current User /me with Bearer token
    me_res = client.get(
        # Execute statement: "/api/v1/auth/me",
        "/api/v1/auth/me",
        # Specify argument: headers={"Authorization": f"Bearer {token}"}
        headers={"Authorization": f"Bearer {token}"},
    )
    # Assert condition: me_res.status_code == 200
    assert me_res.status_code == 200
    # Set me_data to me_res.json()
    me_data = me_res.json()
    # Assert condition: me_data["full_name"] == "Prof. Alan Turing"
    assert me_data["full_name"] == "Prof. Alan Turing"
    # Assert condition: me_data["email"] == unique_email
    assert me_data["email"] == unique_email
    # Assert condition: "hashed_password" not in me_data
    assert "hashed_password" not in me_data

    # 4. Test Login with JSON credentials
    login_res = client.post(
        # Execute statement: "/api/v1/auth/login",
        "/api/v1/auth/login",
        # Execute statement: json={
        json={
            # Define field entry: "email": unique_email
            "email": unique_email,
            # Define field entry: "password": "SecurePassword123!"
            "password": "SecurePassword123!",
        },
    )
    # Assert condition: login_res.status_code == 200
    assert login_res.status_code == 200
    # Assert condition: "access_token" in login_res.json()
    assert "access_token" in login_res.json()
    # Assert condition: login_res.json()["user"]["full_name"] == "Prof. Alan Turing"
    assert login_res.json()["user"]["full_name"] == "Prof. Alan Turing"

    # 5. Test Login with OAuth2 form credentials (username/password)
    oauth_res = client.post(
        # Execute statement: "/api/v1/auth/login",
        "/api/v1/auth/login",
        # Execute statement: data={
        data={
            # Define field entry: "username": unique_email
            "username": unique_email,
            # Define field entry: "password": "SecurePassword123!"
            "password": "SecurePassword123!",
        },
    )
    # Assert condition: oauth_res.status_code == 200
    assert oauth_res.status_code == 200
    # Assert condition: "access_token" in oauth_res.json()
    assert "access_token" in oauth_res.json()
    # Assert condition: oauth_res.json()["user"]["email"] == unique_email
    assert oauth_res.json()["user"]["email"] == unique_email

    # 6. Test invalid password returns 401
    bad_login_res = client.post(
        # Execute statement: "/api/v1/auth/login",
        "/api/v1/auth/login",
        # Execute statement: json={
        json={
            # Define field entry: "email": unique_email
            "email": unique_email,
            # Define field entry: "password": "WrongPassword!"
            "password": "WrongPassword!",
        },
    )
    # Assert condition: bad_login_res.status_code == 401
    assert bad_login_res.status_code == 401

    # 7. Test /auth/me with invalid token returns 401
    bad_me_res = client.get(
        # Execute statement: "/api/v1/auth/me",
        "/api/v1/auth/me",
        # Specify argument: headers={"Authorization": "Bearer invalid_token_xyz"}
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    # Assert condition: bad_me_res.status_code == 401
    assert bad_me_res.status_code == 401


# Define function test_evaluation_with_reference_assignment_and_web_plagiarism
def test_evaluation_with_reference_assignment_and_web_plagiarism():
    # Docstring explaining Verify Gemini evaluator incorporates reference assignments a
    """Verify Gemini evaluator incorporates reference assignments and reports 3-way plagiarism metrics."""
    # Set rubric to [
    rubric = [
        # Define field entry: {"name": "Correctness", "max_score": 50.0, "weight": 50.0, "description": "Correct algorithmic solution"}
        {"name": "Correctness", "max_score": 50.0, "weight": 50.0, "description": "Correct algorithmic solution"},
        # Define field entry: {"name": "Code Style", "max_score": 50.0, "weight": 50.0, "description": "Clean modular implementation"}
        {"name": "Code Style", "max_score": 50.0, "weight": 50.0, "description": "Clean modular implementation"},
    ]
    # Set reference to "def dijkstra(graph, start): heap = [(0, start)] ... optimal benchmark code"
    reference = "def dijkstra(graph, start): heap = [(0, start)] ... optimal benchmark code"
    # Set student_submission to "def dijkstra(g, s): q = [(0, s)] ... student solution"
    student_submission = "def dijkstra(g, s): q = [(0, s)] ... student solution"

    # Set result to gemini_service.evaluate_submission(
    result = gemini_service.evaluate_submission(
        # Specify argument: submission_text=student_submission
        submission_text=student_submission,
        # Specify argument: rubric_criteria=rubric
        rubric_criteria=rubric,
        # Specify argument: assignment_title="Dijkstra Shortest Path"
        assignment_title="Dijkstra Shortest Path",
        # Specify argument: reference_assignment_text=reference
        reference_assignment_text=reference,
    )

    # Assert condition: result.overall_score >= 0.0
    assert result.overall_score >= 0.0
    # Assert condition: len(result.criteria_evaluations) == 2
    assert len(result.criteria_evaluations) == 2
    # Assert condition: result.ai_generated_probability >= 0.0
    assert result.ai_generated_probability >= 0.0
    # Assert condition: result.peer_to_peer_plagiarism_pct is not None
    assert result.peer_to_peer_plagiarism_pct is not None
    # Assert condition: result.web_plagiarism_pct is not None
    assert result.web_plagiarism_pct is not None
    # Assert condition: isinstance(result.web_sources, list)
    assert isinstance(result.web_sources, list)


# Define function test_file_upload_database_persistence_and_retrieval
def test_file_upload_database_persistence_and_retrieval():
    # Docstring explaining Verify uploaded files are saved in the database with file_co
    """Verify uploaded files are saved in the database with file_content and extracted_text."""
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app
    # Import SessionLocal from app.core.database
    from app.core.database import SessionLocal
    # Import Submission from app.models.submission
    from app.models.submission import Submission
    # Import Assignment from app.models.assignment
    from app.models.assignment import Assignment
    # Import Course from app.models.course
    from app.models.course import Course

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set db to SessionLocal()
    db = SessionLocal()

    # Ensure a test course and assignment exist
    try:
        # Set course to db.query(Course).first()
        course = db.query(Course).first()
        # Check if condition: not course
        if not course:
            # Set course to Course(id="c_test_upload", name="Test Course", code="TC101", section="A")
            course = Course(id="c_test_upload", name="Test Course", code="TC101", section="A")
            # Stage entity into database session: db.add(course)
            db.add(course)
            # Commit transaction to database
            db.commit()

        # Set assignment to db.query(Assignment).filter(Assignment.course_id == course.id).first()
        assignment = db.query(Assignment).filter(Assignment.course_id == course.id).first()
        # Check if condition: not assignment
        if not assignment:
            # Set assignment to Assignment(id="assign_test_upload", course_id=course.id, title="Test Assignment")
            assignment = Assignment(id="assign_test_upload", course_id=course.id, title="Test Assignment")
            # Stage entity into database session: db.add(assignment)
            db.add(assignment)
            # Commit transaction to database
            db.commit()
            # Refresh entity state from database: db.refresh(assignment)
            db.refresh(assignment)

        # Upload a code file with auth header
        token = create_access_token("inst_priya_rao")
        # Set headers to {"Authorization": f"Bearer {token}"}
        headers = {"Authorization": f"Bearer {token}"}
        # Set code_content to b"def bubble_sort(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)-i-1):\n            if arr[j] > arr[j+1]: arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n"
        code_content = b"def bubble_sort(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)-i-1):\n            if arr[j] > arr[j+1]: arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n"
        # Set upload_res to client.post(
        upload_res = client.post(
            # Execute statement: f"/api/v1/assignments/{assignment.id}/submissions/batch-upload",
            f"/api/v1/assignments/{assignment.id}/submissions/batch-upload",
            # Specify argument: files=[("files", ("sharma_rahul_sort.py", code_content, "text/x-python"))]
            files=[("files", ("sharma_rahul_sort.py", code_content, "text/x-python"))],
            # Specify argument: headers=headers
            headers=headers,
        )
        # Assert condition: upload_res.status_code == 200, upload_res.text
        assert upload_res.status_code == 200, upload_res.text
        # Set upload_data to upload_res.json()
        upload_data = upload_res.json()
        # Assert condition: upload_data["total_files"] == 1
        assert upload_data["total_files"] == 1
        # Set sub_id to upload_data["submissions"][0]["id"]
        sub_id = upload_data["submissions"][0]["id"]

        # Verify database record
        saved_sub = db.query(Submission).filter(Submission.id == sub_id).first()
        # Assert condition: saved_sub is not None
        assert saved_sub is not None
        # Assert condition: saved_sub.student_name == "Rahul Sharma"
        assert saved_sub.student_name == "Rahul Sharma"
        # Assert condition: saved_sub.file_name == "sharma_rahul_sort.py"
        assert saved_sub.file_name == "sharma_rahul_sort.py"
        # Assert condition: saved_sub.extracted_text is not None
        assert saved_sub.extracted_text is not None
        # Assert condition: "bubble_sort" in saved_sub.extracted_text
        assert "bubble_sort" in saved_sub.extracted_text
        # Assert condition: saved_sub.file_content is not None
        assert saved_sub.file_content is not None
        # Assert condition: "bubble_sort" in saved_sub.file_content
        assert "bubble_sort" in saved_sub.file_content

        # Verify API list returns decrypted student and file info
        list_res = client.get(f"/api/v1/assignments/{assignment.id}/submissions")
        # Assert condition: list_res.status_code == 200
        assert list_res.status_code == 200
        # Set items to list_res.json()
        items = list_res.json()
        # Set matching to [item for item in items if item["id"] == sub_id]
        matching = [item for item in items if item["id"] == sub_id]
        # Assert condition: len(matching) == 1
        assert len(matching) == 1
        # Assert condition: matching[0]["student"] == "Rahul Sharma"
        assert matching[0]["student"] == "Rahul Sharma"
        # Assert condition: matching[0]["file_name"] == "sharma_rahul_sort.py"
        assert matching[0]["file_name"] == "sharma_rahul_sort.py"
    # Execute cleanup block in finally clause
    finally:
        # Execute statement: db.close()
        db.close()


# Define function test_docx_text_extraction_paragraphs_and_tables
def test_docx_text_extraction_paragraphs_and_tables():
    # Docstring explaining Verify python-docx correctly extracts both paragraphs and ta
    """Verify python-docx correctly extracts both paragraphs and table cells."""
    # Import module io
    import io
    # Import module docx
    import docx
    # Import pdf_service from app.services.pdf_service
    from app.services.pdf_service import pdf_service

    # Set doc to docx.Document()
    doc = docx.Document()
    # Execute statement: doc.add_heading("Research Report: Distributed Consensus", level=1)
    doc.add_heading("Research Report: Distributed Consensus", level=1)
    # Execute statement: doc.add_paragraph("This paper analyzes Paxos and Raft consensus protocols u
    doc.add_paragraph("This paper analyzes Paxos and Raft consensus protocols under high network latency.")
    # Execute statement: doc.add_paragraph("Section 2: Comparative Throughput Analysis.")
    doc.add_paragraph("Section 2: Comparative Throughput Analysis.")

    # Set table to doc.add_table(rows=2, cols=3)
    table = doc.add_table(rows=2, cols=3)
    # Set hdr_cells to table.rows[0].cells
    hdr_cells = table.rows[0].cells
    # Set hdr_cells[0].text to "Protocol"
    hdr_cells[0].text = "Protocol"
    # Set hdr_cells[1].text to "Leader Election (ms)"
    hdr_cells[1].text = "Leader Election (ms)"
    # Set hdr_cells[2].text to "Message Complexity"
    hdr_cells[2].text = "Message Complexity"

    # Set row_cells to table.rows[1].cells
    row_cells = table.rows[1].cells
    # Set row_cells[0].text to "Raft"
    row_cells[0].text = "Raft"
    # Set row_cells[1].text to "150ms"
    row_cells[1].text = "150ms"
    # Set row_cells[2].text to "O(n)"
    row_cells[2].text = "O(n)"

    # Set bio to io.BytesIO()
    bio = io.BytesIO()
    # Execute statement: doc.save(bio)
    doc.save(bio)
    # Set docx_bytes to bio.getvalue()
    docx_bytes = bio.getvalue()

    # Set extracted_text to pdf_service.extract_text_from_bytes(docx_bytes, "distributed_consensus.docx")
    extracted_text = pdf_service.extract_text_from_bytes(docx_bytes, "distributed_consensus.docx")
    # Assert condition: extracted_text is not None
    assert extracted_text is not None
    # Assert condition: "Distributed Consensus" in extracted_text
    assert "Distributed Consensus" in extracted_text
    # Assert condition: "Paxos and Raft consensus" in extracted_text
    assert "Paxos and Raft consensus" in extracted_text
    # Assert condition: "Comparative Throughput Analysis" in extracted_text
    assert "Comparative Throughput Analysis" in extracted_text
    # Assert condition: "Protocol | Leader Election (ms) | Message Complexity" in extracted_text
    assert "Protocol | Leader Election (ms) | Message Complexity" in extracted_text
    # Assert condition: "Raft | 150ms | O(n)" in extracted_text
    assert "Raft | 150ms | O(n)" in extracted_text


# Define function test_docx_submission_upload_endpoint
def test_docx_submission_upload_endpoint():
    # Docstring explaining Verify multipart .docx submission uploads parse text and sav
    """Verify multipart .docx submission uploads parse text and save to DB."""
    # Import module io
    import io
    # Import module docx
    import docx
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app
    # Import SessionLocal from app.core.database
    from app.core.database import SessionLocal
    # Import Assignment from app.models.assignment
    from app.models.assignment import Assignment
    # Import Course from app.models.course
    from app.models.course import Course
    # Import Submission from app.models.submission
    from app.models.submission import Submission

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set db to SessionLocal()
    db = SessionLocal()
    # Begin try block to handle operations safely
    try:
        # Set course to db.query(Course).first()
        course = db.query(Course).first()
        # Check if condition: not course
        if not course:
            # Set course to Course(id="c_docx_test", name="Docx Course", code="DC101")
            course = Course(id="c_docx_test", name="Docx Course", code="DC101")
            # Stage entity into database session: db.add(course)
            db.add(course)
            # Commit transaction to database
            db.commit()

        # Set assignment to db.query(Assignment).filter(Assignment.course_id == course.id).first()
        assignment = db.query(Assignment).filter(Assignment.course_id == course.id).first()
        # Check if condition: not assignment
        if not assignment:
            # Set assignment to Assignment(id="assign_docx_test", course_id=course.id, title="Docx Assignment")
            assignment = Assignment(id="assign_docx_test", course_id=course.id, title="Docx Assignment")
            # Stage entity into database session: db.add(assignment)
            db.add(assignment)
            # Commit transaction to database
            db.commit()

        # Build in-memory docx
        doc = docx.Document()
        # Execute statement: doc.add_paragraph("Student analysis on deep learning transformers and atten
        doc.add_paragraph("Student analysis on deep learning transformers and attention mechanisms.")
        # Set bio to io.BytesIO()
        bio = io.BytesIO()
        # Execute statement: doc.save(bio)
        doc.save(bio)
        # Set docx_bytes to bio.getvalue()
        docx_bytes = bio.getvalue()

        # Upload via /api/v1/assignments/{assignment_id}/submissions with auth header
        token = create_access_token("inst_priya_rao")
        # Set headers to {"Authorization": f"Bearer {token}"}
        headers = {"Authorization": f"Bearer {token}"}
        # Set res to client.post(
        res = client.post(
            # Execute statement: f"/api/v1/assignments/{assignment.id}/submissions",
            f"/api/v1/assignments/{assignment.id}/submissions",
            # Specify argument: files={"file": ("deep_learning_essay.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            files={"file": ("deep_learning_essay.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            # Specify argument: data={"student_name": "Maya Patel", "student_roll": "2024-555"}
            data={"student_name": "Maya Patel", "student_roll": "2024-555"},
            # Specify argument: headers=headers
            headers=headers,
        )
        # Assert condition: res.status_code == 200, res.text
        assert res.status_code == 200, res.text
        # Set data to res.json()
        data = res.json()
        # Assert condition: data["student"] == "Maya Patel"
        assert data["student"] == "Maya Patel"
        # Assert condition: data["file_name"] == "deep_learning_essay.docx"
        assert data["file_name"] == "deep_learning_essay.docx"
        # Assert condition: data["status"] == "pending"
        assert data["status"] == "pending"

        # Set sub_id to data["id"]
        sub_id = data["id"]
        # Set saved to db.query(Submission).filter(Submission.id == sub_id).first()
        saved = db.query(Submission).filter(Submission.id == sub_id).first()
        # Assert condition: saved is not None
        assert saved is not None
        # Assert condition: saved.student_name == "Maya Patel"
        assert saved.student_name == "Maya Patel"
        # Assert condition: saved.extracted_text is not None
        assert saved.extracted_text is not None
        # Assert condition: "deep learning transformers" in saved.extracted_text
        assert "deep learning transformers" in saved.extracted_text
        # Assert condition: saved.content is not None
        assert saved.content is not None
        # Assert condition: "deep learning transformers" in saved.content
        assert "deep learning transformers" in saved.content
    # Execute cleanup block in finally clause
    finally:
        # Execute statement: db.close()
        db.close()


# Define function test_gemini_schema_bidirectional_mapping
def test_gemini_schema_bidirectional_mapping():
    # Docstring explaining Verify StructuredGradingOutput models validate all required 
    """Verify StructuredGradingOutput models validate all required audit keys."""
    # Import ( from app.schemas.grading
    from app.schemas.grading import (
        # Execute statement: StructuredGradingOutput,
        StructuredGradingOutput,
        # Execute statement: GradingSummary,
        GradingSummary,
        # Execute statement: RubricBreakdownItem,
        RubricBreakdownItem,
        # Execute statement: IntegrityAudit,
        IntegrityAudit,
        # Execute statement: PeerPlagiarismAudit,
        PeerPlagiarismAudit,
        # Execute statement: WebPlagiarismAudit,
        WebPlagiarismAudit,
        # Execute statement: WebSourceItem,
        WebSourceItem,
        # Execute statement: AIContentAssessment,
        AIContentAssessment,
        # Execute statement: FeedbackDetails,
        FeedbackDetails,
    )

    # Set data to {
    data = {
        # Execute statement: "grading_summary": {
        "grading_summary": {
            # Define field entry: "score": 88.0
            "score": 88.0,
            # Define field entry: "max_points": 100.0
            "max_points": 100.0,
            # Define field entry: "percentage": 88.0
            "percentage": 88.0,
            # Define field entry: "grade": "B+"
            "grade": "B+",
        },
        # Execute statement: "rubric_breakdown": [
        "rubric_breakdown": [
            # Execute statement: {
            {
                # Define field entry: "criterion_name": "Technical Depth"
                "criterion_name": "Technical Depth",
                # Define field entry: "awarded_points": 28.0
                "awarded_points": 28.0,
                # Define field entry: "max_points": 30.0
                "max_points": 30.0,
                # Define field entry: "rationale": "Clear algorithmic analysis with rigorous asymptotic bounds."
                "rationale": "Clear algorithmic analysis with rigorous asymptotic bounds.",
            }
        ],
        # Execute statement: "integrity_audit": {
        "integrity_audit": {
            # Execute statement: "peer_plagiarism": {
            "peer_plagiarism": {
                # Define field entry: "similarity_percentage": 5.2
                "similarity_percentage": 5.2,
                # Define field entry: "matched_peer_id": "STUDENT_A"
                "matched_peer_id": "STUDENT_A",
                # Define field entry: "matching_excerpts": ["standard library initialization"]
                "matching_excerpts": ["standard library initialization"],
            },
            # Execute statement: "web_plagiarism": {
            "web_plagiarism": {
                # Define field entry: "similarity_percentage": 12.0
                "similarity_percentage": 12.0,
                # Execute statement: "matched_sources": [
                "matched_sources": [
                    # Execute statement: {
                    {
                        # Define field entry: "url": "https://en.wikipedia.org/wiki/Quicksort"
                        "url": "https://en.wikipedia.org/wiki/Quicksort",
                        # Define field entry: "title": "Quicksort - Wikipedia"
                        "title": "Quicksort - Wikipedia",
                        # Define field entry: "snippet": "Quicksort is an efficient divide-and-conquer sorting algorithm."
                        "snippet": "Quicksort is an efficient divide-and-conquer sorting algorithm.",
                        # Define field entry: "match_pct": 12.0
                        "match_pct": 12.0,
                    }
                ],
            },
            # Execute statement: "ai_content_assessment": {
            "ai_content_assessment": {
                # Define field entry: "likelihood_rating": "low"
                "likelihood_rating": "low",
                # Define field entry: "ai_probability": 8.5
                "ai_probability": 8.5,
                # Define field entry: "stylistic_indicators": ["Varied sentence structure and idiosyncratic code formatting."]
                "stylistic_indicators": ["Varied sentence structure and idiosyncratic code formatting."],
            },
        },
        # Execute statement: "feedback": {
        "feedback": {
            # Define field entry: "strengths": ["Strong theoretical foundation", "Clear diagrams"]
            "strengths": ["Strong theoretical foundation", "Clear diagrams"],
            # Define field entry: "actionable_corrections": ["Add empirical benchmarks for non-uniform data."]
            "actionable_corrections": ["Add empirical benchmarks for non-uniform data."],
            # Define field entry: "summary": "Solid submission demonstrating good domain grasp."
            "summary": "Solid submission demonstrating good domain grasp.",
        },
    }

    # Set output to StructuredGradingOutput(**data)
    output = StructuredGradingOutput(**data)
    # Assert condition: output.overall_score == 88.0
    assert output.overall_score == 88.0
    # Assert condition: output.grading_summary.percentage == 88.0
    assert output.grading_summary.percentage == 88.0
    # Assert condition: output.integrity_audit.peer_plagiarism.similarity_percentage == 5.2
    assert output.integrity_audit.peer_plagiarism.similarity_percentage == 5.2
    # Assert condition: output.integrity_audit.web_plagiarism.similarity_percentage == 12.0
    assert output.integrity_audit.web_plagiarism.similarity_percentage == 12.0
    # Assert condition: len(output.integrity_audit.web_plagiarism.matched_sources) == 1
    assert len(output.integrity_audit.web_plagiarism.matched_sources) == 1
    # Assert condition: output.integrity_audit.web_plagiarism.matched_sources[0].url == "https://en.wikipedia.org/wiki/Quicksort"
    assert output.integrity_audit.web_plagiarism.matched_sources[0].url == "https://en.wikipedia.org/wiki/Quicksort"
    # Assert condition: output.integrity_audit.ai_content_assessment.ai_probability == 8.5
    assert output.integrity_audit.ai_content_assessment.ai_probability == 8.5
    # Assert condition: len(output.feedback.strengths) == 2
    assert len(output.feedback.strengths) == 2


# Define function test_assignment_creation_and_supabase_sync
def test_assignment_creation_and_supabase_sync():
    # Docstring explaining Verify /assignments endpoint creates assignment with UUID, s
    """Verify /assignments endpoint creates assignment with UUID, syncs course, and sets up evaluation."""
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app
    # Import SessionLocal from app.core.database
    from app.core.database import SessionLocal
    # Import Assignment from app.models.assignment
    from app.models.assignment import Assignment

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set res to client.post(
    res = client.post(
        # Execute statement: "/api/v1/assignments",
        "/api/v1/assignments",
        # Execute statement: json={
        json={
            # Define field entry: "course_id": "c_cs201"
            "course_id": "c_cs201",
            # Define field entry: "title": "CS201 · Data Structures - Section A Assignment"
            "title": "CS201 · Data Structures - Section A Assignment",
            # Define field entry: "description": "Sorting algorithms and tree traversal implementation."
            "description": "Sorting algorithms and tree traversal implementation.",
            # Define field entry: "reference_assignment_text": "Reference Exemplar: Dijkstra and Quicksort with complexity analysis."
            "reference_assignment_text": "Reference Exemplar: Dijkstra and Quicksort with complexity analysis.",
        },
    )
    # Assert condition: res.status_code == 200, res.text
    assert res.status_code == 200, res.text
    # Set data to res.json()
    data = res.json()
    # Set assign_id to data["id"]
    assign_id = data["id"]
    # Assert condition: assign_id.startswith("assign_")
    assert assign_id.startswith("assign_")
    # Assert condition: data["title"] == "CS201 · Data Structures - Section A Assignment"
    assert data["title"] == "CS201 · Data Structures - Section A Assignment"

    # Verify local DB persistence
    db = SessionLocal()
    # Begin try block to handle operations safely
    try:
        # Set assign to db.query(Assignment).filter(Assignment.id == assign_id).first()
        assign = db.query(Assignment).filter(Assignment.id == assign_id).first()
        # Assert condition: assign is not None
        assert assign is not None
        # Assert condition: assign.reference_assignment_text is not None
        assert assign.reference_assignment_text is not None

        # Trigger evaluation on this assignment ID
        eval_res = client.post(
            # Execute statement: f"/api/v1/assignments/{assign_id}/evaluate",
            f"/api/v1/assignments/{assign_id}/evaluate",
            # Specify argument: json={"similarity_threshold": 90.0}
            json={"similarity_threshold": 90.0},
        )
        # Assert condition: eval_res.status_code == 200, eval_res.text
        assert eval_res.status_code == 200, eval_res.text
        # Set eval_data to eval_res.json()
        eval_data = eval_res.json()
        # Assert condition: eval_data["status"] in ("queued", "processing", "completed")
        assert eval_data["status"] in ("queued", "processing", "completed")
    # Execute cleanup block in finally clause
    finally:
        # Execute statement: db.close()
        db.close()


# Define function test_evaluation_fallback_for_unregistered_assignment_id
def test_evaluation_fallback_for_unregistered_assignment_id():
    # Docstring explaining Verify that evaluating an unregistered/temporary assignment 
    """Verify that evaluating an unregistered/temporary assignment ID dynamically creates it without crashing."""
    # Import TestClient from fastapi.testclient
    from fastapi.testclient import TestClient
    # Import app from app.main
    from app.main import app
    # Import module uuid
    import uuid

    # Set client to TestClient(app)
    client = TestClient(app)
    # Set temp_id to f"a_{uuid.uuid4().hex[:8]}"
    temp_id = f"a_{uuid.uuid4().hex[:8]}"

    # Evaluating a non-existent assignment ID should self-heal and not throw 404/500
    eval_res = client.post(
        # Execute statement: f"/api/v1/assignments/{temp_id}/evaluate",
        f"/api/v1/assignments/{temp_id}/evaluate",
        # Execute statement: json={
        json={
            # Define field entry: "title": "Dynamic Fallback Assignment"
            "title": "Dynamic Fallback Assignment",
            # Define field entry: "reference_assignment_text": "Dynamic benchmark solution."
            "reference_assignment_text": "Dynamic benchmark solution.",
            # Define field entry: "similarity_threshold": 90.0
            "similarity_threshold": 90.0,
        },
    )
    # Assert condition: eval_res.status_code == 200, eval_res.text
    assert eval_res.status_code == 200, eval_res.text
    # Set eval_data to eval_res.json()
    eval_data = eval_res.json()
    # Assert condition: eval_data["status"] in ("queued", "processing", "completed")
    assert eval_data["status"] in ("queued", "processing", "completed")


def test_db_resilience_and_pool_status():
    """Verify persistent connection pool configuration, keep-alives, and health diagnostics."""
    from app.core.database import get_db_pool_status, check_db_health
    from app.core.config import settings

    status = get_db_pool_status()
    assert "pool_type" in status
    assert status["pool_size"] == settings.DB_POOL_SIZE
    assert status["max_overflow"] == settings.DB_MAX_OVERFLOW
    assert status["pool_recycle_seconds"] == 1800
    assert status["pool_pre_ping"] is True
    assert status["keepalives_enabled"] is True

    health = check_db_health()
    assert health["status"] == "healthy"
    assert health["connected"] is True
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0.0


def test_db_retry_with_backoff_decorator():
    """Verify db_retry_with_backoff catches transient connection errors and recovers."""
    from app.core.database import db_retry_with_backoff
    from sqlalchemy.exc import OperationalError

    attempts = 0

    @db_retry_with_backoff(max_retries=3, initial_delay=0.05, backoff_factor=1.5)
    def flaky_db_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise OperationalError("SELECT 1", {}, Exception("Connection reset by peer"))
        return "success"

    result = flaky_db_operation()
    assert result == "success"
    assert attempts == 2


def test_db_health_api_endpoint():
    """Verify /api/health/db and /health/db endpoints return live latency and pool metrics."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/health/db")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["connected"] is True
    assert "latency_ms" in data
    assert "pool" in data
    assert data["pool"]["pool_recycle_seconds"] == 1800


def test_student_deletion_and_cascade():
    """Verify student deletion endpoint removes roster entry and cascades/unlinks cleanly."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import SessionLocal
    from app.models.classroom import Classroom
    from app.models.student import Student
    from app.models.course import Course
    from app.models.submission import Submission
    from app.models.assignment import Assignment
    from app.models.instructor import Instructor
    import uuid

    client = TestClient(app)
    db = SessionLocal()
    try:
        # Create test instructor and course/classroom
        inst_id = f"inst_del_{uuid.uuid4().hex[:6]}"
        instructor = Instructor(
            id=inst_id,
            name="Dr. Delete Test",
            email=f"{inst_id}@univ.edu",
            hashed_password="hash",
        )
        db.add(instructor)

        c_id = f"cls_del_{uuid.uuid4().hex[:6]}"
        classroom = Classroom(
            id=c_id,
            name="Deletion Test Classroom",
            code="DEL101",
            instructor_id=inst_id,
        )
        db.add(classroom)
        course = Course(
            id=c_id,
            name="Deletion Test Classroom",
            code="DEL101",
            section="A",
            instructor_id=inst_id,
        )
        db.add(course)

        # Enroll test student
        st_id = f"st_del_{uuid.uuid4().hex[:6]}"
        student = Student(
            id=st_id,
            classroom_id=c_id,
            roll_number="DEL-001",
            full_name="Student To Delete",
            email="to.delete@univ.edu",
        )
        db.add(student)

        # Create linked submission
        assign_id = f"as_del_{uuid.uuid4().hex[:6]}"
        assignment = Assignment(id=assign_id, course_id=c_id, title="Del Assignment")
        db.add(assignment)

        sub_id = f"sub_del_{uuid.uuid4().hex[:6]}"
        sub = Submission(
            id=sub_id,
            assignment_id=assign_id,
            classroom_id=c_id,
            student_id=st_id,
            student_name_encrypted=ferpa_cipher.encrypt("Student To Delete"),
            student_roll_encrypted=ferpa_cipher.encrypt("DEL-001"),
            student_email_encrypted=ferpa_cipher.encrypt("to.delete@univ.edu"),
            file_name="student_project.py",
        )
        db.add(sub)
        db.commit()

        # Delete student via API
        from app.core.security import create_access_token
        auth_token = create_access_token(inst_id)
        del_res = client.delete(
            f"/api/v1/classrooms/{c_id}/students/{st_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert del_res.status_code == 204

        # Verify student is removed
        assert db.query(Student).filter(Student.id == st_id).first() is None

        # Verify submission has student_id unlinked rather than corrupted
        saved_sub = db.query(Submission).filter(Submission.id == sub_id).first()
        assert saved_sub is not None
        assert saved_sub.student_id is None

        # Verify 404 for repeated deletion
        del_again = client.delete(
            f"/api/v1/classrooms/{c_id}/students/{st_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert del_again.status_code == 404
    finally:
        db.close()


def test_session_invalidation_on_logout():
    """Verify session is explicitly terminated in database and invalidated on logout."""
    from fastapi.testclient import TestClient
    from app.main import app
    import uuid

    client = TestClient(app)
    unique_email = f"session_test_{uuid.uuid4().hex[:6]}@univ.edu"

    # Sign up
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Session Tester",
            "email": unique_email,
            "password": "Password123!",
            "role": "Instructor",
        },
    )
    assert signup_res.status_code == 201
    token = signup_res.json()["access_token"]

    # Verify access with active token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email

    # Explicit logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200

    # Subsequent request with invalidated token must be rejected
    rejected_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rejected_res.status_code == 401
    assert "terminated" in rejected_res.json()["detail"].lower()





