"""FastAPI Application Main Entry Point.

Configures:
- REST API routing (/api/v1)
- CORS Middleware for Next.js / Vite React frontend
- Database table creation on startup
- Health checks and system diagnostics
"""

from contextlib import asynccontextmanager
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base, check_db_health, TRANSIENT_DB_EXCEPTIONS
from app.core.logging import logger
from app.api.v1.api_router import api_v1_router
from app.api.health import router as health_router, db_health_check, health_check as comprehensive_health_check
import app.models  # noqa


class DatabaseResilienceMiddleware:
    """Pure ASGI middleware catching transient database connection drops and logging reconnection events."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except TRANSIENT_DB_EXCEPTIONS as exc:
            logger.error(
                f"[DB-DROPPED] Database connection dropped during request {scope.get('method')} {scope.get('path')}: {exc}"
            )
            response = JSONResponse(
                status_code=503,
                content={
                    "error": "Database connection drop detected",
                    "detail": "Transient connection reset or severed socket. Connection pool is auto-reconnecting.",
                    "status": "reconnecting",
                },
                headers={"Retry-After": "1"},
            )
            await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """Pure ASGI middleware injecting standard HTTP security and privacy compliance headers."""

    def __init__(self, app):
        # Store inner ASGI application
        self.app = app

    async def __call__(self, scope, receive, send):
        # Ignore non-HTTP scopes
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Wrapper function intercepting response start to inject compliance headers
        async def send_with_security_headers(message):
            # Check for response start event
            if message["type"] == "http.response.start":
                # Convert headers to list
                headers_list = list(message.get("headers", []))
                # Append standard security and privacy compliance headers
                headers_list.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ])
                # Assign augmented headers
                message["headers"] = headers_list

            # Forward message
            await send(message)

        # Delegate execution with wrapped send callback
        await self.app(scope, receive, send_with_security_headers)


# Define asynchronous lifespan context manager managing application startup and shutdown hooks
@asynccontextmanager
# Function definition accepting FastAPI instance and yielding runtime context
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures.

    Validates required environment variables (DATABASE_URL, SECRET_KEY, GEMINI_API_KEY)
    and asserts database connectivity upon application initialization.
    """
    # Log startup announcement for the backend service
    logger.info("Initializing Verism AI Backend Service...")

    # Validate required environment variables at startup
    missing_vars = []
    # Verify DATABASE_URL is non-empty
    if not settings.DATABASE_URL or not str(settings.DATABASE_URL).strip():
        missing_vars.append("DATABASE_URL")
    # Verify auth secret (SECRET_KEY or JWT_SECRET) is non-empty
    auth_secret = settings.JWT_SECRET or settings.SECRET_KEY
    if not auth_secret or not str(auth_secret).strip():
        missing_vars.append("SECRET_KEY (or JWT_SECRET)")
    # Verify GEMINI_API_KEY is non-empty (allow bypass only in dedicated testing mode)
    is_testing = os.getenv("TESTING") == "1" or "pytest" in sys.modules
    if not is_testing and (not settings.GEMINI_API_KEY or not str(settings.GEMINI_API_KEY).strip()):
        missing_vars.append("GEMINI_API_KEY")

    # If any required environment variable is missing, fail fast with a descriptive RuntimeError
    if missing_vars:
        error_msg = (
            f"Startup validation failed: Missing required environment variable(s): {', '.join(missing_vars)}. "
            "Please configure them in your .env file or server environment before starting the service."
        )
        logger.critical(f"[STARTUP] {error_msg}")
        raise RuntimeError(error_msg)

    # Wrap startup verification in try block to log database connectivity diagnostics
    try:
        # Import database health check utility function
        from app.core.database import check_db_health
        # Execute live database health probe against configured PostgreSQL connection
        db_health = check_db_health()
        # Verify if database connection was successfully established
        if db_health.get("connected"):
            # Log successful database connection and latency
            logger.info(
                f"[STARTUP] Database connection verified ({db_health.get('dialect')}, "
                f"latency: {db_health.get('latency_ms')}ms). Schema managed via Alembic migrations."
            )
        # Handle unhealthy database state
        else:
            # Log critical warning with error details
            logger.critical(
                f"[STARTUP] Database connectivity probe returned unhealthy: {db_health.get('error')}"
            )
    # Catch any unexpected startup inspection errors
    except Exception as e:
        # Log critical error notice
        logger.critical(f"[STARTUP] Database startup verification failed: {e}")
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
    # Loopback IP address on port 3000
    "http://127.0.0.1:3000",
    # Loopback IP address on port 5173
    "http://127.0.0.1:5173",
    # Loopback IP address on port 8080
    "http://127.0.0.1:8080",
    # Specific production Vercel deployment URL
    "https://assessment-project-o64i.vercel.app",  # Your specific Vercel URL
    # Current active Vercel deployment URL
    "https://assessment-project-jycg.vercel.app",
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

# Add Database Resilience Middleware to catch transient connection drops
app.add_middleware(DatabaseResilienceMiddleware)
# Add Security and Privacy Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

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

# Mount health diagnostic router
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix="/api")
app.include_router(health_router)


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


# Live database health probe endpoint with latency and pool status
@app.get("/api/health/db", tags=["Health"])
@app.get("/health/db", tags=["Health"])
def health_db():
    """Live database connectivity probe returning latency and pool status."""
    return db_health_check()


# Health diagnostic endpoint returning comprehensive system status and component checks
@app.get("/health", tags=["Health"])
# Handler function for health check probe
def health_check():
    """Lightweight comprehensive health check verifying database, Gemini API, and storage.

    Returns:
        JSONResponse: Detailed diagnostic status payload for all core services.
    """
    # Delegate to comprehensive diagnostic handler checking database, Gemini, and storage
    return comprehensive_health_check()
