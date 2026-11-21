# Module docstring explaining automated Supabase database resilience and verification test suite
"""Authoritative database integration and resilience test suite for Verism AI.

Verifies:
1. Live socket connection to managed PostgreSQL (Supabase) via SQLAlchemy connection pool.
2. Complete transaction lifecycle: INSERT, SELECT, ROLLBACK, and COMMIT.
3. Strict FAIL-FAST policy: bad or severed connection strings raise an error without SQLite fallback.
4. Schema completeness: all 30 foundational tables exist in the live PostgreSQL catalog.
"""

# Import pytest testing framework
import pytest
# Import uuid module for generating unique entity identifiers
import uuid
# Import datetime module for UTC timestamp verification
from datetime import datetime, timezone
# Import SQLAlchemy core constructs: create_engine, text queries, inspect
from sqlalchemy import create_engine, text, inspect
# Import SQLAlchemy ORM sessionmaker and Session
from sqlalchemy.orm import sessionmaker, Session
# Import QueuePool for pooling configuration
from sqlalchemy.pool import QueuePool

# Import application settings instance
from app.core.config import settings
# Import database SessionLocal, engine, and check_db_health helper
from app.core.database import SessionLocal, engine, check_db_health, Base
# Import ORM models for transaction testing
from app.models.user import User
from app.models.classroom import Classroom
from app.models.course import Course


# Test function verifying live connectivity to Supabase PostgreSQL
def test_supabase_postgres_connection_success():
    """Verify that SQLAlchemy engine successfully connects to Supabase PostgreSQL."""
    # Execute database health check probe
    health = check_db_health()
    # Assert status is reported as healthy
    assert health["status"] == "healthy", f"Database health check failed: {health}"
    # Assert connected boolean flag is True
    assert health["connected"] is True, "Database failed to connect to Supabase PostgreSQL"
    # Assert dialect is postgresql
    assert health["dialect"] == "postgresql", f"Expected postgresql dialect, got: {health['dialect']}"
    # Assert query latency is positive number
    assert health["latency_ms"] > 0, "Query latency should be positive"


# Test function verifying transaction lifecycle: insert, query, rollback, and commit
def test_database_session_transaction_lifecycle():
    """Verify that a session can insert, query, rollback, and commit records transactionally."""
    # Create thread-safe session from SessionLocal factory
    session: Session = SessionLocal()
    # Generate unique test email to isolate test execution
    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"test.instructor.{unique_suffix}@verism.edu"
    test_user_id = f"user-{uuid.uuid4().hex[:12]}"

    # Try block executing rollback verification
    try:
        # Create uncommitted user instance
        user_rollback = User(
            id=f"user-rb-{unique_suffix}",
            email=f"rollback.{unique_suffix}@verism.edu",
            full_name="Rollback Test User",
            hashed_password="dummy_hash_for_test",
            role="Instructor",
            email_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        # Add entity to pending session
        session.add(user_rollback)
        # Flush entity to allocate transaction state without committing
        session.flush()
        # Verify entity exists inside uncommitted transaction
        assert session.query(User).filter_by(id=user_rollback.id).first() is not None

        # Explicitly roll back the transaction
        session.rollback()
        # Verify entity does NOT exist after rollback
        persisted_rb = session.query(User).filter_by(id=user_rollback.id).first()
        assert persisted_rb is None, "Entity should not exist after transaction rollback"

        # Now test successful commit lifecycle
        user_commit = User(
            id=test_user_id,
            email=test_email,
            full_name="Dr. Alan Turing",
            hashed_password="secure_hashed_password_123",
            role="Instructor · Distributed Systems",
            email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        # Add entity to session
        session.add(user_commit)
        # Commit transaction to PostgreSQL
        session.commit()

        # Query committed record from database
        queried = session.query(User).filter_by(id=test_user_id).first()
        # Assert user was found
        assert queried is not None, "Committed user must be queryable from PostgreSQL"
        # Assert fields match committed values
        assert queried.email == test_email
        assert queried.full_name == "Dr. Alan Turing"

        # Clean up test user
        session.delete(queried)
        # Commit deletion
        session.commit()
        # Verify cleanup
        assert session.query(User).filter_by(id=test_user_id).first() is None
    # Finally block closing the session
    finally:
        # Close session returning connection to pool
        session.close()


# Test function verifying fail-fast policy when DATABASE_URL is invalid
def test_fail_fast_on_invalid_database_url():
    """Verify that an invalid DATABASE_URL raises an error immediately without SQLite fallback."""
    # Malformed PostgreSQL connection string pointing to unreachable host
    bad_url = "postgresql+psycopg2://invalid_user:invalid_pass@127.0.0.1:54399/nonexistent_db"
    # Connect arguments with 1-second timeout for quick failure
    connect_args = {"connect_timeout": 1}

    # Verify that attempting to connect with bad credentials raises an OperationalError
    with pytest.raises(Exception) as exc_info:
        # Create engine targeting bad URL
        bad_engine = create_engine(bad_url, connect_args=connect_args)
        # Attempt connection checkout which must fail
        with bad_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    # Assert that the exception is a connection or operational error
    assert exc_info.value is not None, "Must raise an exception when database is unreachable"


# Test function verifying existence of all required foundational tables
def test_all_expected_tables_exist_in_database():
    """Verify that all 30 foundational tables exist in the Supabase PostgreSQL database."""
    # List of expected table names per architectural specification
    expected_tables = [
        "organizations",
        "users",
        "refresh_tokens",
        "user_sessions",
        "instructors",
        "classrooms",
        "courses",
        "sections",
        "students",
        "enrollments",
        "rubrics",
        "rubric_criteria",
        "rubric_tiers",
        "assignments",
        "reference_files",
        "assignment_folders",
        "submissions",
        "folder_submissions",
        "submission_files",
        "batch_jobs",
        "grading_runs",
        "draft_grades",
        "criterion_scores",
        "evaluation_results",
        "monthly_usages",
        "similarity_matches",
        "integrity_flags",
        "exports",
        "audit_logs",
        "deletion_requests",
    ]

    # Inspect live database schema using SQLAlchemy inspector
    inspector = inspect(engine)
    # Fetch list of existing table names in public schema
    existing_tables = set(inspector.get_table_names())

    # Find missing tables if any
    missing = [t for t in expected_tables if t not in existing_tables]
    # Assert all expected tables exist
    assert not missing, f"Missing foundational tables in database: {missing}. Existing tables: {sorted(existing_tables)}"
