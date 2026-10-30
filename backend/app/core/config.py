"""Application configuration using Pydantic Settings v2.

Manages all environment variables for PostgreSQL, Redis, Celery, Qdrant,
Gemini GenAI, FERPA/GDPR encryption, and CORS settings.
"""

# Import typing utilities for complex type hints across settings models
from typing import List, Union, Optional
# Import json module to parse serialized JSON environment variables (such as CORS origins)
import json
# Import os module to resolve directory paths and read environment variables
import os
# Import AnyHttpUrl type and field_validator decorator from pydantic for custom validation
from pydantic import AnyHttpUrl, field_validator
# Graceful import handling for Pydantic v1 versus Pydantic v2 settings classes
try:
    # Attempt to import BaseSettings and SettingsConfigDict from pydantic_settings (Pydantic v2)
    from pydantic_settings import BaseSettings, SettingsConfigDict
# Fallback for environments using legacy Pydantic v1
except ImportError:
    # Import legacy BaseSettings from pydantic root
    from pydantic import BaseSettings
    # Define SettingsConfigDict as None to signal legacy configuration mode
    SettingsConfigDict = None  # type: ignore

# Compute absolute path to the backend directory hosting application files
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Construct absolute path to the .env file in the backend directory
_ENV_FILE_PATH = os.path.join(_BACKEND_DIR, ".env")
# Define tuple of env files to search in priority order
_ENV_FILES = (_ENV_FILE_PATH, ".env")
# Compute default SQLite database file path normalized with forward slashes
_DEFAULT_DB_PATH = os.path.join(_BACKEND_DIR, "verism.db").replace("\\", "/")


# Configuration class defining application environment variables and default values
class Settings(BaseSettings):
    # App Information
    # Deployment environment designation (development, staging, production)
    APP_ENV: str = "development"
    # Debug mode flag enabling detailed error traces and auto-reload
    DEBUG: bool = True
    # Human-readable title of the backend service displayed in OpenAPI docs
    PROJECT_NAME: str = "Verism AI Backend"
    # Root URL prefix for REST API version 1 endpoints
    API_V1_STR: str = "/api/v1"
    # Default network port number on which the ASGI web server listens
    PORT: int = 8000
    # Host network interface address to bind (0.0.0.0 binds to all available interfaces)
    HOST: str = "0.0.0.0"

    # Security & FERPA/GDPR Encryption
    # Cryptographic secret key used for signing JWT access tokens
    SECRET_KEY: str = "verism_super_secret_jwt_key_change_in_production_1234567890"
    # Optional alternative JWT secret key read from cloud environment variables
    JWT_SECRET: Optional[str] = None
    # Access token lifespan in minutes (defaults to 1440 minutes / 24 hours)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    # AES-256 / Fernet key used to encrypt student PII at rest for FERPA compliance
    FERPA_ENCRYPTION_KEY: str = "MbGUys4qem_FHtZy_5zx8bBSrxkTI2UWrjnhrFAHcyY="

    # Validator reconciling SECRET_KEY with JWT_SECRET if present in environment
    @field_validator("SECRET_KEY", mode="before")
    # Class method validator operating before field type conversion
    @classmethod
    def assemble_secret_key(cls, v: str) -> str:
        # Check if JWT_SECRET environment variable is explicitly set
        jwt_sec = os.getenv("JWT_SECRET")
        # If set, prioritize JWT_SECRET over default SECRET_KEY
        if jwt_sec:
            # Return custom JWT secret
            return jwt_sec
        # Otherwise return current value
        return v

    # CORS Origins
    # List of allowed origins for Cross-Origin Resource Sharing (CORS)
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        # Local Vite development server on port 3000
        "http://localhost:3000",
        # Local Vite development server on port 5173
        "http://localhost:5173",
        # Loopback IP address on port 3000
        "http://127.0.0.1:3000",
        # Loopback IP address on port 5173
        "http://127.0.0.1:5173",
        # Alternate frontend port 8080
        "http://localhost:8080",
        # Production Vercel deployment URL
        "https://assessment-project-o64i.vercel.app",
    ]

    # Validator parsing JSON arrays or comma-separated strings into a Python list
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    # Class method validator for CORS origins
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        # Handle string representation of CORS origins
        if isinstance(v, str):
            # Check if string is formatted as a JSON array
            if v.startswith("[") and v.endswith("]"):
                # Attempt to parse JSON array
                try:
                    # Deserialize JSON string to list of origins
                    return json.loads(v)
                # Catch JSON syntax error
                except Exception:
                    # Fall through to comma-separated parsing
                    pass
            # Split comma-separated string and strip whitespace
            return [i.strip() for i in v.split(",") if i.strip()]
        # Return existing list unchanged
        elif isinstance(v, list):
            # Return list of origins
            return v
        # Default fallback allowing all origins
        return ["*"]

    # Supabase Layer – set USE_SUPABASE=false to skip and use local PostgreSQL only
    # Boolean toggle determining whether Supabase cloud integration is active
    USE_SUPABASE: bool = False
    # Supabase project URL endpoint
    SUPABASE_URL: str = "https://lzranjtbiucfaktbnjec.supabase.co"
    # Supabase anonymous public client key
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6cmFuanRiaXVjZmFrdGJuamVjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIzNDAyMTMsImV4cCI6MjEwNzkxNjIxM30.TWBIc8-chcw7aI2LYX8NEiopKWMz9-wNB9oqTKe5q9s"
    # Supabase privileged service role secret key
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database (SQLite default for embedded development, PostgreSQL supported)
    # Database connection string URI (PostgreSQL or SQLite)
    DATABASE_URL: str = f"sqlite:///{_DEFAULT_DB_PATH}"
    # PostgreSQL host hostname
    POSTGRES_SERVER: str = "localhost"
    # PostgreSQL TCP port number
    POSTGRES_PORT: int = 5432
    # PostgreSQL authentication username
    POSTGRES_USER: str = "postgres"
    # PostgreSQL authentication password
    POSTGRES_PASSWORD: str = "postgres"
    # Target database name inside PostgreSQL
    POSTGRES_DB: str = "verism_db"

    # Local File Storage (replaces Supabase Storage when USE_SUPABASE=false)
    # Local filesystem directory path for storing uploaded student submission files
    UPLOADS_DIR: str = "./uploads"

    # Redis & Celery
    # Redis server hostname for task broker and caching
    REDIS_HOST: str = "localhost"
    # Redis TCP port number
    REDIS_PORT: int = 6379
    # Redis connection URL string
    REDIS_URL: str = "redis://localhost:6379/0"
    # Celery task queue broker connection URL
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    # Celery task execution result backend URL
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Qdrant Vector DB (Embedded in-memory mode by default)
    # Qdrant vector database server hostname
    QDRANT_HOST: str = "localhost"
    # Qdrant vector database TCP port number
    QDRANT_PORT: int = 6333
    # Qdrant service URL (:memory: enables embedded in-memory mode)
    QDRANT_URL: str = ":memory:"
    # Optional API key for hosted Qdrant Cloud clusters
    QDRANT_API_KEY: str = ""
    # Target vector collection name storing document embeddings
    QDRANT_COLLECTION_NAME: str = "verism_submissions"

    # Google GenAI (Gemini 2.5 Flash / Pro)
    # API key for Google Gemini GenAI services
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Default LLM model identifier for grading and feedback evaluation
    GEMINI_MODEL: str = "gemini-flash-latest"
    # Default text embedding model identifier for vector indexing
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # Evaluation Thresholds
    # Default percentage threshold flagging peer-to-peer collision matches (90%)
    DEFAULT_SIMILARITY_THRESHOLD: float = 90.0
    # Default probability threshold triggering the AI-content indicator flag (65%)
    AI_CONTENT_INDICATOR_THRESHOLD: float = 65.0

    # Check if Pydantic v2 SettingsConfigDict is available
    if SettingsConfigDict is not None:
        # Configure model settings via Pydantic v2 SettingsConfigDict
        model_config = SettingsConfigDict(
            # Specify env files to search
            env_file=_ENV_FILES,
            # Specify UTF-8 encoding for .env files
            env_file_encoding="utf-8",
            # Enforce case sensitivity for environment variable keys
            case_sensitive=True,
            # Ignore extra unexpected environment variables without raising errors
            extra="ignore",
        )
    # Fallback configuration for Pydantic v1
    else:
        # Inner Config class for Pydantic v1 configuration
        class Config:
            # Specify env files to search
            env_file = _ENV_FILES
            # Enforce case sensitivity
            case_sensitive = True
            # Ignore extra environment variables
            extra = "ignore"


# Instantiate and export the global application settings singleton
settings = Settings()
