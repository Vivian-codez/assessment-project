"""Application configuration using Pydantic Settings v2.

Manages all environment variables for PostgreSQL, Redis, Celery, Qdrant,
Gemini GenAI, FERPA/GDPR encryption, and CORS settings.
"""

from typing import List, Union
import json
import os
from pydantic import AnyHttpUrl, field_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None  # type: ignore

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_FILE_PATH = os.path.join(_BACKEND_DIR, ".env")
_ENV_FILES = (_ENV_FILE_PATH, ".env")
_DEFAULT_DB_PATH = os.path.join(_BACKEND_DIR, "verism.db").replace("\\", "/")


class Settings(BaseSettings):
    # App Information
    APP_ENV: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Verism AI Backend"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & FERPA/GDPR Encryption
    SECRET_KEY: str = "verism_super_secret_jwt_key_change_in_production_1234567890"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    FERPA_ENCRYPTION_KEY: str = "MbGUys4qem_FHtZy_5zx8bBSrxkTI2UWrjnhrFAHcyY="

    # CORS Origins
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Supabase Layer (Active Supabase Connection via supabase-py)
    SUPABASE_URL: str = "https://bziehnbdeczqtaemelkw.supabase.co"
    SUPABASE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_anon_key_for_development"
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database (SQLite default for embedded development, PostgreSQL supported)
    DATABASE_URL: str = f"sqlite:///{_DEFAULT_DB_PATH}"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "verism_db"

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Qdrant Vector DB (Embedded in-memory mode by default)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = ":memory:"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "verism_submissions"

    # Google GenAI (Gemini 2.5 Flash / Pro)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # Evaluation Thresholds
    DEFAULT_SIMILARITY_THRESHOLD: float = 90.0
    AI_CONTENT_INDICATOR_THRESHOLD: float = 65.0

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=_ENV_FILES,
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )
    else:
        class Config:
            env_file = _ENV_FILES
            case_sensitive = True
            extra = "ignore"


settings = Settings()
