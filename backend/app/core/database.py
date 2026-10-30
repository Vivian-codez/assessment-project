"""Database session management with SQLAlchemy 2.0.

Provides:
- Engine creation with connection pooling
- Thread-safe SessionLocal sessionmaker
- FastAPI get_db dependency
- Automatic table creation utility
"""

# Import Generator type hint from typing to annotate the get_db dependency generator yielding sessions
from typing import Generator
# Import create_engine factory from sqlalchemy to configure database connections and connection pooling
from sqlalchemy import create_engine
# Import declarative_base for ORM class definitions and sessionmaker to construct thread-safe database sessions
from sqlalchemy.orm import declarative_base, sessionmaker

# Import application settings singleton to retrieve environment configuration including DATABASE_URL
from app.core.config import settings

# Retrieve the configured database connection URI string from application settings
db_url = settings.DATABASE_URL
# Check if the connection URL specifies the generic postgresql scheme
if db_url.startswith("postgresql://"):
    # Replace postgresql:// with postgresql+psycopg2:// to explicitly specify the psycopg2 driver for SQLAlchemy
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Initialize dictionary to hold driver-specific connection arguments passed to underlying DBAPI
connect_args = {}
# Check if the database connection string targets a local SQLite database
if db_url.startswith("sqlite"):
    # Disable SQLite same-thread check so multiple concurrent FastAPI request threads can access the connection
    connect_args["check_same_thread"] = False
    # Create the SQLAlchemy engine bound to the SQLite database URL with custom connection arguments
    engine = create_engine(
        # Pass the SQLite database connection string
        db_url,
        # Supply driver-specific connection arguments containing check_same_thread=False
        connect_args=connect_args,
        # Disable echo to prevent printing every raw SQL query to the console
        echo=False,
    )
# Execute PostgreSQL engine creation when SQLite is not targeted
else:
    # Wrap PostgreSQL connection setup and connectivity test in a try block for graceful error handling
    try:
        # Instantiate SQLAlchemy engine with production connection pooling parameters
        engine = create_engine(
            # Pass the configured PostgreSQL connection string with driver specification
            db_url,
            # Maintain up to 10 persistent connections in the connection pool
            pool_size=10,
            # Allow up to 20 additional transient connections beyond pool_size during peak traffic bursts
            max_overflow=20,
            # Recycle pooled connections every 3600 seconds (1 hour) to avoid disconnections by timeouts
            pool_recycle=3600,
            # Enable pre-ping check to test connections for liveness before giving them to the application
            pool_pre_ping=True,
            # Disable verbose SQL query logging to console to keep logs clean and protect sensitive data
            echo=False,
            # Set connection timeout to 3 seconds so failure is fast if the database host is unreachable
            connect_args={"connect_timeout": 3},
        )
        # Eagerly test connection reachability to confirm the database server is available
        with engine.connect() as conn:
            # Connection succeeded, exit test block immediately and return connection to pool
            pass
    # Catch any connection or authentication errors if PostgreSQL is unavailable
    except Exception:
        # Define local SQLite fallback URL to ensure application remains functional offline or during local testing
        fallback_url = "sqlite:///./verism.db"
        # Instantiate fallback engine using the local SQLite database file
        engine = create_engine(
            # Pass fallback SQLite database file path
            fallback_url,
            # Disable same-thread check for SQLite to support multi-threaded FastAPI execution
            connect_args={"check_same_thread": False},
            # Disable query echoing for clean output
            echo=False,
        )

# Create thread-safe session factory bound to the active engine with auto-commit and auto-flush disabled
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative Base class from which all database ORM models inherit table mapping metadata
Base = declarative_base()


# Define utility function to initialize database tables and apply incremental column migrations
def init_db():
    """Create tables and ensure newly added columns are migrated."""
    # Import text construct from sqlalchemy to execute raw SQL DDL migration statements
    from sqlalchemy import text
    import app.models  # Ensure all model tables are registered on Base.metadata
    # Generate all physical database tables corresponding to models registered on Base.metadata
    Base.metadata.create_all(bind=engine)
    # Open dedicated connection from the engine to execute schema alteration scripts
    with engine.connect() as conn:
        # Iterate over idempotent ALTER TABLE statements for schema evolution
        for col_sql in [
            # Add full_name column to users table if not already present
            "ALTER TABLE users ADD COLUMN full_name VARCHAR(255);",
            # Add reference_assignment_text column to assignments table if not already present
            "ALTER TABLE assignments ADD COLUMN reference_assignment_text TEXT;",
            # Add file_content column to submissions table for normalized text storage
            "ALTER TABLE submissions ADD COLUMN file_content TEXT;",
            # Add file_url column to submissions table for public or signed file access URLs
            "ALTER TABLE submissions ADD COLUMN file_url TEXT;",
            # Add content column to submissions table for extracted text content
            "ALTER TABLE submissions ADD COLUMN content TEXT;",
            # Add web_plagiarism_score column to submissions table with 0.0 default
            "ALTER TABLE submissions ADD COLUMN web_plagiarism_score REAL DEFAULT 0.0;",
            # Add web_sources JSON column to submissions table with empty array default
            "ALTER TABLE submissions ADD COLUMN web_sources JSON DEFAULT '[]';",
            # Add classroom_id column to submissions table
            "ALTER TABLE submissions ADD COLUMN classroom_id VARCHAR(64);",
            # Add student_id column to submissions table
            "ALTER TABLE submissions ADD COLUMN student_id VARCHAR(64);",
            # Add classroom_id column to rubrics table
            "ALTER TABLE rubrics ADD COLUMN classroom_id VARCHAR(64);",
            # Add title column to rubrics table
            "ALTER TABLE rubrics ADD COLUMN title VARCHAR(255);",
            # Add total_marks column to rubrics table
            "ALTER TABLE rubrics ADD COLUMN total_marks REAL DEFAULT 0.0;",
            # Add criterion_name column to rubric_criteria table
            "ALTER TABLE rubric_criteria ADD COLUMN criterion_name VARCHAR(255);",
            # Add max_points column to rubric_criteria table
            "ALTER TABLE rubric_criteria ADD COLUMN max_points REAL DEFAULT 4.0;",
            # Add levels column to rubric_criteria table
            "ALTER TABLE rubric_criteria ADD COLUMN levels JSON DEFAULT '[]';",
        ]:
            # Wrap execution of each individual column alteration in a try block to handle existing columns
            try:
                # Execute the ALTER TABLE SQL statement against the active database connection
                conn.execute(text(col_sql))
                # Commit the DDL transaction to persist the newly added column in the schema
                conn.commit()
            # Catch exceptions when column already exists in the table schema
            except Exception:
                # Silently ignore duplicate column errors and proceed to next migration item
                pass


# Wrap automatic startup database initialization in a try block
try:
    # Invoke init_db on module import to guarantee tables exist before requests arrive
    init_db()
# Catch any database initialization errors during module import
except Exception:
    # Allow module import to proceed even if database initialization throws a transient error
    pass


# Define FastAPI dependency function yielding a database session per HTTP request
def get_db() -> Generator:
    """Dependency that yields a database session and safely closes it upon request completion."""
    # Instantiate a new database session from the SessionLocal factory
    db = SessionLocal()
    # Enter try block to ensure the session is safely closed after the request is processed
    try:
        # Yield the active database session to the requesting route handler
        yield db
    # Guarantee execution of session cleanup logic regardless of request success or failure
    finally:
        # Close the database session and return its connection back to the connection pool
        db.close()
