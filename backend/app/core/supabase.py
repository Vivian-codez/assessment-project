"""Supabase Client Initialization using supabase-py.

Leverages the existing Supabase environment variables and PostgREST client.
"""

from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

__all__ = ["supabase", "create_client", "Client"]
