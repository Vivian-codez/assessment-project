"""Migrate database columns and users table."""
from sqlalchemy import text
from app.core.database import engine, Base
import app.models

Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    # Add reference_assignment_text to assignments if not exists
    conn.execute(text("""
        ALTER TABLE assignments ADD COLUMN IF NOT EXISTS reference_assignment_text TEXT;
    """))
    # Add web_plagiarism_score and web_sources to submissions if not exists
    conn.execute(text("""
        ALTER TABLE submissions ADD COLUMN IF NOT EXISTS web_plagiarism_score FLOAT DEFAULT 0.0;
    """))
    conn.execute(text("""
        ALTER TABLE submissions ADD COLUMN IF NOT EXISTS web_sources JSON DEFAULT '[]';
    """))
    conn.commit()

print("Local PostgreSQL schema migrated successfully!")
