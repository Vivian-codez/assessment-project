"""Database session management with SQLAlchemy 2.0.

Provides:
- Engine creation with connection pooling
- Thread-safe SessionLocal sessionmaker
- FastAPI get_db dependency
- Automatic table creation utility
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Configure engine arguments with resilient fallback
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
    )
else:
    try:
        engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False,
            connect_args={"connect_timeout": 3},
        )
        # Test connection eagerly to verify server availability
        with engine.connect() as conn:
            pass
    except Exception:
        # Fallback to local SQLite if PostgreSQL connection fails
        fallback_url = "sqlite:///./verism.db"
        engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create tables and ensure newly added columns are migrated."""
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for col_sql in [
            "ALTER TABLE assignments ADD COLUMN reference_assignment_text TEXT;",
            "ALTER TABLE submissions ADD COLUMN file_content TEXT;",
            "ALTER TABLE submissions ADD COLUMN web_plagiarism_score REAL DEFAULT 0.0;",
            "ALTER TABLE submissions ADD COLUMN web_sources JSON DEFAULT '[]';",
        ]:
            try:
                conn.execute(text(col_sql))
                conn.commit()
            except Exception:
                pass


try:
    init_db()
except Exception:
    pass



def get_db() -> Generator:
    """Dependency that yields a database session and safely closes it upon request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
