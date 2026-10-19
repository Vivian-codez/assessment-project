"""Supabase Client Initialization using supabase-py.

Leverages SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (falling back to SUPABASE_KEY).
Includes safety wrappers for connection resilience.
"""

from typing import Optional
from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import logger

_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip() if settings.SUPABASE_SERVICE_ROLE_KEY else settings.SUPABASE_KEY.strip()

try:
    supabase: Client = create_client(settings.SUPABASE_URL, _key)
    logger.info(f"Supabase client initialized successfully with endpoint {settings.SUPABASE_URL}")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    # Initialize with default/anon key as fallback
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as fallback_err:
        logger.error(f"Supabase fallback client initialization failed: {fallback_err}")
        supabase = None  # type: ignore

__all__ = ["supabase", "create_client", "Client"]
