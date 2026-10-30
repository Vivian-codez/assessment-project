"""
Supabase Client – Optional Integration Layer.

When settings.USE_SUPABASE is False (the default for local Docker deployments),
this module returns a lightweight no-op stub so all existing call-sites that
wrap Supabase calls in try/except continue to silently fall through to their
local SQLAlchemy fallback without raising import errors.

When USE_SUPABASE is True the real supabase-py client is initialised against
settings.SUPABASE_URL / SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY).
"""

# Import Any and Optional typing primitives for type annotations
from typing import Any, Optional
# Import global settings object to inspect configuration parameters
from app.core.config import settings
# Import application logger for runtime logging
from app.core.logging import logger


class _NoOpResponse:
    """Mimics a supabase-py APIResponse with empty data so fallback code runs."""
    # Data attribute returning an empty list mimicking an empty query result set
    data: list = []
    # Count attribute returning None mimicking no counted rows
    count: Optional[int] = None


class _NoOpChain:
    """Chainable no-op that returns itself for every fluent query method call."""

    def __getattr__(self, _name: str) -> "_NoOpChain":
        # Intercept any method access (select, eq, order, limit, etc.) and return self
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> "_NoOpChain":
        # Intercept any method call with arbitrary arguments and return self
        return self

    def execute(self) -> _NoOpResponse:
        # Terminal query execution method returning an empty _NoOpResponse object
        return _NoOpResponse()


class _NoOpAuth:
    """Stub for supabase.auth – raises on auth calls so callers use local JWT path."""

    def get_user(self, *args: Any, **kwargs: Any) -> None:
        # Raise error to trigger caller's local JWT fallback
        raise RuntimeError("Supabase auth is disabled (USE_SUPABASE=false)")

    def sign_in_with_password(self, *args: Any, **kwargs: Any) -> None:
        # Raise error to trigger caller's local password verification
        raise RuntimeError("Supabase auth is disabled (USE_SUPABASE=false)")

    def sign_up(self, *args: Any, **kwargs: Any) -> None:
        # Raise error to trigger caller's local user registration
        raise RuntimeError("Supabase auth is disabled (USE_SUPABASE=false)")

    def sign_out(self, *args: Any, **kwargs: Any) -> None:
        # No-op sign out handler that succeeds silently
        pass

    def get_session(self, *args: Any, **kwargs: Any) -> None:
        # Raise error indicating that Supabase session retrieval is disabled
        raise RuntimeError("Supabase auth is disabled (USE_SUPABASE=false)")

    def on_auth_state_change(self, *args: Any, **kwargs: Any) -> None:
        # No-op auth state event listener subscription
        pass


class _NoOpStorage:
    """Stub for supabase.storage – raises on storage bucket operations so local disk is used."""

    def from_(self, *args: Any, **kwargs: Any) -> "_NoOpChain":
        # Raise error to route file persistence calls to local filesystem UPLOADS_DIR
        raise RuntimeError("Supabase storage is disabled (USE_SUPABASE=false)")


class _NoOpClient:
    """Complete no-op Supabase client used when USE_SUPABASE=false."""

    # Attach the no-op authentication handler instance
    auth = _NoOpAuth()
    # Attach the no-op cloud storage handler instance
    storage = _NoOpStorage()

    # Provide a dummy supabase_url attribute to avoid AttributeError in legacy loggers
    supabase_url: str = "local"

    def table(self, _name: str) -> _NoOpChain:
        # Return a chainable fluent no-op query builder for table operations
        return _NoOpChain()

    def from_(self, *args: Any, **kwargs: Any) -> _NoOpChain:
        # Return a chainable fluent no-op query builder for PostgREST from_ calls
        return _NoOpChain()


# ── Initialise ────────────────────────────────────────────────────────────────

# Check if the USE_SUPABASE configuration flag is enabled
if settings.USE_SUPABASE:
    # Attempt to initialize the real Supabase client library
    try:
        # Import create_client and Client type from the external supabase library
        from supabase import create_client, Client as _Client
        # Select the service role key if available, otherwise fall back to the anon key
        _key = (
            settings.SUPABASE_SERVICE_ROLE_KEY.strip()
            if settings.SUPABASE_SERVICE_ROLE_KEY
            else settings.SUPABASE_KEY.strip()
        )
        # Instantiate the live Supabase client using the target URL and key
        supabase: Any = create_client(settings.SUPABASE_URL, _key)
        # Log successful initialization of the live Supabase client
        logger.info(f"Supabase client initialised → {settings.SUPABASE_URL}")
    # Catch any connection or initialization errors
    except Exception as exc:
        # Log error details and fallback to the no-op client stub
        logger.error(f"Supabase client init failed, using no-op stub: {exc}")
        # Assign the no-op stub instance to supabase
        supabase: Any = _NoOpClient()
# If USE_SUPABASE is False, instantiate the no-op stub directly
else:
    # Assign the no-op stub instance to supabase
    supabase: Any = _NoOpClient()
    # Log that local PostgreSQL mode is active with Supabase stubbed out
    logger.info("USE_SUPABASE=false – using local PostgreSQL only (Supabase stub active)")

# Define public module exports
__all__ = ["supabase"]
