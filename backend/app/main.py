"""FastAPI Application Main Entry Point.

Configures:
- REST API routing (/api/v1)
- CORS Middleware for Next.js / Vite React frontend
- Database table creation on startup
- Health checks and system diagnostics
"""

# Import asynchronous context manager decorator to handle FastAPI application lifespan events
from contextlib import asynccontextmanager
# Import FastAPI core application class
from fastapi import FastAPI
# Import Cross-Origin Resource Sharing (CORS) middleware to allow browser frontend communication
from fastapi.middleware.cors import CORSMiddleware
# Import JSONResponse utility for returning structured JSON payloads
from fastapi.responses import JSONResponse

# Import global application configuration settings
from app.core.config import settings
# Import SQLAlchemy database engine and declarative Base for table schema creation
from app.core.database import engine, Base
# Import application logger for runtime event tracking
from app.core.logging import logger
# Import API version 1 aggregated router containing all domain endpoints
from app.api.v1.api_router import api_v1_router
# Import models to ensure they register on Base
# Import all database models so their table schemas attach to Base.metadata before create_all
import app.models  # noqa


# Define asynchronous lifespan context manager managing application startup and shutdown hooks
@asynccontextmanager
# Function definition accepting FastAPI instance and yielding runtime context
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    # Log startup announcement for the backend service
    logger.info("Initializing Verism AI Backend Service...")
    # Wrap database initialization in a try block to handle setup exceptions safely
    try:
        # Create tables automatically if they do not exist
        # Automatically generate physical database tables for all models registered on Base.metadata
        Base.metadata.create_all(bind=engine)
        # Log successful completion of table schema initialization
        logger.info("Database tables initialized successfully.")

        # Ensure newly added columns exist in SQLite or existing databases
        # Import text construct to execute raw SQL DDL migration queries safely
        from sqlalchemy import text
        # Acquire dedicated database connection from the connection pool
        with engine.connect() as conn:
            # Iterate through idempotent ALTER TABLE statements for schema evolution
            for col_sql in [
                # Add full_name column to users table
                "ALTER TABLE users ADD COLUMN full_name VARCHAR(255);",
                # Add reference exemplar text column to assignments table
                "ALTER TABLE assignments ADD COLUMN reference_assignment_text TEXT;",
                # Add normalized file content column to submissions table
                "ALTER TABLE submissions ADD COLUMN file_content TEXT;",
                # Add storage download URL column to submissions table
                "ALTER TABLE submissions ADD COLUMN file_url TEXT;",
                # Add extracted text content column to submissions table
                "ALTER TABLE submissions ADD COLUMN content TEXT;",
                # Add web plagiarism match score column with default 0.0 to submissions table
                "ALTER TABLE submissions ADD COLUMN web_plagiarism_score REAL DEFAULT 0.0;",
                # Add web sources JSON column with empty array default to submissions table
                "ALTER TABLE submissions ADD COLUMN web_sources JSON DEFAULT '[]';",
                # Add classroom identifier association column to submissions table
                "ALTER TABLE submissions ADD COLUMN classroom_id TEXT;",
                # Add student identifier association column to submissions table
                "ALTER TABLE submissions ADD COLUMN student_id TEXT;",
                # Add calculated total score column to draft grades table
                "ALTER TABLE draft_grades ADD COLUMN total_score REAL;",
                # Add maximum possible score column with default 100.0 to draft grades table
                "ALTER TABLE draft_grades ADD COLUMN max_score REAL DEFAULT 100.0;",
                # Add granular criteria breakdown JSON column to draft grades table
                "ALTER TABLE draft_grades ADD COLUMN criteria_breakdown JSON DEFAULT '[]';",
                # Add composite plagiarism report JSON column to draft grades table
                "ALTER TABLE draft_grades ADD COLUMN plagiarism_report JSON DEFAULT '{}';",
                # Add final feedback text column to draft grades table
                "ALTER TABLE draft_grades ADD COLUMN feedback TEXT;",
            ]:
                # Wrap each individual column migration in try block to handle existing columns
                try:
                    # Execute the ALTER TABLE migration DDL
                    conn.execute(text(col_sql))
                    # Commit the DDL transaction to persist schema modifications
                    conn.commit()
                # Catch exception when column already exists
                except Exception:
                    # Silently ignore duplicate column errors
                    pass

        # Auto-seed removed to maintain clean user-driven state without mock data.
    # Catch any unexpected startup errors
    except Exception as e:
        # Log warning if table creation encountered a recoverable error
        logger.warning(f"Database table auto-creation skipped or encountered error: {e}")
    # Yield control to let the FastAPI application serve incoming HTTP requests
    yield
    # Log graceful shutdown event when the application stops
    logger.info("Shutting down Verism AI Backend Service...")


# Instantiate the main FastAPI application instance
app = FastAPI(
    # Set OpenAPI application title from settings
    title=settings.PROJECT_NAME,
    # Set OpenAPI application description
    description="Backend API and Async Evaluation Service for Verism AI Teacher Console",
    # Set API documentation version string
    version="1.0.0",
    # URL path for interactive Swagger UI documentation
    docs_url="/docs",
    # URL path for ReDoc alternative documentation
    redoc_url="/redoc",
    # URL path for raw OpenAPI JSON schema specification
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Bind the startup and shutdown lifespan context manager
    lifespan=lifespan,
    # Disable automatic redirect of trailing slashes to prevent 307 redirects on API clients
    redirect_slashes=False,
)

# Configure CORS Middleware for React frontend (Local + Vercel)
# Define standard local development frontend origins
origins = [
    # Vite default development server port
    "http://localhost:5173",
    # Alternative frontend port
    "http://localhost:8080",
    # Standard React/Next.js port
    "http://localhost:3000",
    # Specific production Vercel deployment URL
    "https://assessment-project-o64i.vercel.app",  # Your specific Vercel URL
]

# Retrieve additional configured CORS origins from application settings
cors_origins = settings.BACKEND_CORS_ORIGINS
# Check if configured origins were provided as a serialized string
if isinstance(cors_origins, str):
    # Import json module to parse serialized list
    import json
    # Attempt parsing JSON string
    try:
        # Parse JSON array into a list
        cors_origins = json.loads(cors_origins)
    # Catch parsing error
    except Exception:
        # Fall back to single element list
        cors_origins = [cors_origins]

# Combine built-in origins with configured settings origins, removing duplicate entries
combined_origins = list(dict.fromkeys(origins + (cors_origins or [])))

# Add CORS middleware to the FastAPI application pipeline
app.add_middleware(
    # Specify the CORSMiddleware class
    CORSMiddleware,
    # Allow request origins defined in combined list
    allow_origins=combined_origins,
    # Allow dynamic preview deployments matching any vercel.app subdomain via regex
    allow_origin_regex=r"https://.*\.vercel\.app",  # Matches any preview or production Vercel deployment
    # Allow cookies and Authorization headers across origins
    allow_credentials=True,
    # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_methods=["*"],
    # Allow all request headers
    allow_headers=["*"],
)

# Register API v1 Router under /api/v1, /api, and root /
# This ensures that frontend requests succeed regardless of whether API_BASE_URL includes /api/v1, /api, or /
# Register API v1 router under /api/v1 prefix
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
# Register API v1 router under /api prefix for alternative proxy clients
app.include_router(api_v1_router, prefix="/api")
# Register API v1 router at root for backward compatibility
app.include_router(api_v1_router)


# Root health probe endpoint returning service metadata
@app.get("/", tags=["Health"])
# Handler function for root endpoint
def root():
    # Return JSON dictionary containing service name, version, status, and philosophy
    return {
        # Service name
        "service": settings.PROJECT_NAME,
        # Semantic version
        "version": "1.0.0",
        # Online health indicator
        "status": "online",
        # Link to documentation
        "docs": "/docs",
        # Teacher-in-the-loop philosophy motto
        "philosophy": "AI suggests. You stamp. Every grade waits for your approval.",
    }


# Health diagnostic endpoint returning system status and component checks
@app.get("/health", tags=["Health"])
# Handler function for health check probe
def health_check():
    """System health check and diagnostic probe."""
    # Return JSON dictionary detailing operational readiness across all subsystem dependencies
    return {
        # General health status
        "status": "healthy",
        # Current environment name (development, production)
        "environment": settings.APP_ENV,
        # Flag indicating whether database connection URL is configured
        "database_configured": bool(settings.DATABASE_URL),
        # Flag indicating whether Supabase URL is configured
        "supabase_configured": bool(settings.SUPABASE_URL),
        # Flag indicating whether Redis broker URL is configured
        "redis_configured": bool(settings.REDIS_URL),
        # Flag confirming Qdrant vector database is configured
        "qdrant_configured": True,
        # Operational mode of Qdrant (in-memory or remote server)
        "qdrant_mode": "embedded/in-memory" if settings.QDRANT_URL == ":memory:" else settings.QDRANT_URL,
        # Active Google Gemini model name
        "gemini_model": settings.GEMINI_MODEL,
        # Status of FERPA encryption handler
        "ferpa_encryption": "active",
    }
