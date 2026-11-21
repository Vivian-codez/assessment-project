# Docstring: Migrate database columns and users table.
"""Migrate database columns and users table."""
# Import text from sqlalchemy
from sqlalchemy import text
# Import engine, Base from app.core.database
from app.core.database import engine, Base
# Import module app.models
import app.models

# Execute statement: Base.metadata.create_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Manage context with engine.connect() as conn
with engine.connect() as conn:
    # Add reference_assignment_text to assignments if not exists
    # Execute statement: conn.execute(text("""
    conn.execute(text("""
        ALTER TABLE assignments ADD COLUMN IF NOT EXISTS reference_assignment_text TEXT;
    """))
    # Add web_plagiarism_score and web_sources to submissions if not exists
    # Execute statement: conn.execute(text("""
    conn.execute(text("""
        ALTER TABLE submissions ADD COLUMN IF NOT EXISTS web_plagiarism_score FLOAT DEFAULT 0.0;
    """))
    # Execute statement: conn.execute(text("""
    conn.execute(text("""
        ALTER TABLE submissions ADD COLUMN IF NOT EXISTS web_sources JSON DEFAULT '[]';
    """))
    # Execute statement: conn.commit()
    conn.commit()

# Print output: print("Local PostgreSQL schema migrated successfully!")
print("Local PostgreSQL schema migrated successfully!")
