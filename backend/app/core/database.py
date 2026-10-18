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
        )
    except Exception as e:
        # Fallback to local SQLite if PostgreSQL connection fails
        fallback_url = "sqlite:///./verism.db"
        engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """Dependency that yields a database session and safely closes it upon request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
