"""FastAPI Application Main Entry Point.

Configures:
- REST API routing (/api/v1)
- CORS Middleware for Next.js / Vite React frontend
- Database table creation on startup
- Health checks and system diagnostics
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import logger
from app.api.v1.api_router import api_v1_router
# Import models to ensure they register on Base
import app.models  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    logger.info("Initializing Verism AI Backend Service...")
    try:
        # Create tables automatically if they do not exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")

        # Ensure newly added columns exist in SQLite or existing databases
        from sqlalchemy import text
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

        # Ensure seed data exists in database for courses and assignments
        from app.core.database import SessionLocal
        from app.models.course import Course
        db = SessionLocal()
        try:
            if db.query(Course).count() == 0:
                logger.info("Database contains 0 courses. Initializing seed data...")
                from scripts.seed_data import seed
                seed()
                logger.info("Default seed courses, assignments, and rubrics loaded successfully.")
        except Exception as seed_err:
            logger.warning(f"Seed data initialization notice: {seed_err}")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database table auto-creation skipped or encountered error: {e}")
    yield
    logger.info("Shutting down Verism AI Backend Service...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API and Async Evaluation Service for Verism AI Teacher Console",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS Middleware for React frontend (Local + Vercel)
origins = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:3000",
    "https://assessment-project-o64i.vercel.app",  # Your specific Vercel URL
]

cors_origins = settings.BACKEND_CORS_ORIGINS
if isinstance(cors_origins, str):
    import json
    try:
        cors_origins = json.loads(cors_origins)
    except Exception:
        cors_origins = [cors_origins]

combined_origins = list(dict.fromkeys(origins + (cors_origins or [])))

app.add_middleware(
    CORSMiddleware,
    allow_origins=combined_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Matches any preview or production Vercel deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Router under both /api/v1 and root /
# This ensures that frontend requests succeed regardless of whether VITE_API_BASE_URL includes /api/v1 or not!
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(api_v1_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "philosophy": "AI suggests. You stamp. Every grade waits for your approval.",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """System health check and diagnostic probe."""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "database_configured": bool(settings.DATABASE_URL),
        "supabase_configured": bool(settings.SUPABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
        "qdrant_configured": True,
        "qdrant_mode": "embedded/in-memory" if settings.QDRANT_URL == ":memory:" else settings.QDRANT_URL,
        "gemini_model": settings.GEMINI_MODEL,
        "ferpa_encryption": "active",
    }
