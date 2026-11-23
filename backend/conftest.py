# Module docstring explaining session-wide Pytest test configuration and environment defaults
"""Pytest configuration and session-wide fixtures for Verism AI backend test suite."""

# Import os module for configuring process-level test environment variables
import os
# Import sys module for managing path resolution
import sys

# Set execution environment mode to test
os.environ["APP_ENV"] = "test"
# Set isolated SQLite test database URI
os.environ["DATABASE_URL"] = "sqlite:///./ci_test.db"
# Ensure dummy cryptographic JWT secret key is configured for tests
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-for-automated-verification-32ch")
# Ensure dummy Gemini API key is configured for test mock execution
os.environ.setdefault("GEMINI_API_KEY", "ci-dummy-gemini-key-for-test-mocking")
# Disable remote Supabase cloud client sync in isolated tests
os.environ.setdefault("USE_SUPABASE", "false")
