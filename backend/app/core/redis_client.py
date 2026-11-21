# Module docstring explaining Redis client, rate limiting, and token deny-list helpers
"""Redis client connection pool, rate limiting, and token deny-list management.

Provides:
- Shared redis.Redis client with connection pooling and fast timeout handling
- Token deny-list operations for invalidated JWT access tokens
- Sliding window rate limiting for login attempts with in-memory fallback
"""

# Import time module for timestamp tracking in seconds
import time
# Import typing helpers for type annotations
from typing import Optional, Tuple, Set, Dict
# Import application settings singleton
from app.core.config import settings
# Import application logger
from app.core.logging import logger

# Graceful import of redis library
try:
    # Attempt to import redis client
    import redis
    # Flag indicating redis library is installed
    _REDIS_INSTALLED = True
# Catch missing package error
except ImportError:
    # Set flag to False
    _REDIS_INSTALLED = False
    # Set redis reference to None
    redis = None  # type: ignore

# Global Redis client singleton reference
_redis_client: Optional["redis.Redis"] = None
# In-memory token deny-list fallback: dict mapping token to expiration epoch timestamp
_memory_denylist: Dict[str, float] = {}
# In-memory rate limit fallback: dict mapping key to list of request epoch timestamps
_memory_rate_limits: Dict[str, list] = {}


def get_redis_client() -> Optional["redis.Redis"]:
    """Retrieve or initialize the global Redis client instance.

    Returns None if Redis is unavailable or unconfigured, enabling in-memory fallback.
    """
    global _redis_client
    # Return cached client if already initialized
    if _redis_client is not None:
        return _redis_client

    # Verify redis package is installed and URL is configured
    if not _REDIS_INSTALLED or not settings.REDIS_URL:
        return None

    try:
        # Create client with 1.0s timeout to avoid blocking requests
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            decode_responses=True,
        )
        # Test connection with ping
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.debug(f"[REDIS] Redis client unavailable ({exc}); falling back to in-memory store.")
        return None


def add_token_to_denylist(token: str, ttl_seconds: int = 900) -> None:
    """Add a revoked JWT token to the Redis deny-list with automatic TTL expiration.

    Args:
        token: Raw JWT access token string to invalidate
        ttl_seconds: Remaining lifespan of the token in seconds (default: 15 mins)
    """
    if not token:
        return

    r = get_redis_client()
    if r:
        try:
            # Set key with prefix and expiration
            r.setex(f"denylist:{token}", ttl_seconds, "revoked")
            return
        except Exception as e:
            logger.warning(f"[REDIS-DENYLIST] Failed to write to Redis ({e}); storing in memory.")

    # In-memory fallback
    expire_at = time.time() + ttl_seconds
    _memory_denylist[token] = expire_at
    # Clean up expired entries in memory
    now = time.time()
    expired_keys = [k for k, exp in _memory_denylist.items() if exp < now]
    for k in expired_keys:
        _memory_denylist.pop(k, None)


def is_token_denylisted(token: str) -> bool:
    """Check if a JWT access token has been revoked in the deny-list.

    Args:
        token: Raw JWT access token string

    Returns:
        True if the token is revoked, False if still valid
    """
    if not token:
        return False

    r = get_redis_client()
    if r:
        try:
            # Check existence in Redis
            return bool(r.exists(f"denylist:{token}"))
        except Exception as e:
            logger.debug(f"[REDIS-DENYLIST] Redis read notice ({e}); checking in-memory.")

    # Check in-memory store
    now = time.time()
    expire_at = _memory_denylist.get(token)
    if expire_at is not None:
        if expire_at > now:
            return True
        else:
            # Token already expired
            _memory_denylist.pop(token, None)
            return False

    return False


def check_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> Tuple[bool, int]:
    """Sliding-window rate limiter preventing brute-force attacks on sensitive endpoints.

    Args:
        key: Unique identifier string (e.g. 'login:127.0.0.1' or 'login:user@email.com')
        max_attempts: Maximum allowed requests within the time window (default: 5)
        window_seconds: Time window duration in seconds (default: 300 / 5 minutes)

    Returns:
        Tuple of (allowed: bool, remaining_attempts: int)
    """
    now = time.time()
    r = get_redis_client()

    if r:
        try:
            redis_key = f"ratelimit:{key}"
            # Pipeline commands to atomically record request and check count
            pipe = r.pipeline()
            # Remove timestamps outside current sliding window
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            # Add current timestamp
            pipe.zadd(redis_key, {str(now): now})
            # Count elements in window
            pipe.zcard(redis_key)
            # Set TTL on the sorted set
            pipe.expire(redis_key, window_seconds)
            results = pipe.execute()

            current_count = results[2]
            if current_count > max_attempts:
                return False, 0
            return True, max(0, max_attempts - current_count)
        except Exception as e:
            logger.debug(f"[REDIS-RATELIMIT] Redis rate limit notice ({e}); using memory.")

    # In-memory sliding window fallback
    timestamps = _memory_rate_limits.setdefault(key, [])
    # Filter timestamps to within the active window
    cutoff = now - window_seconds
    valid_timestamps = [t for t in timestamps if t > cutoff]
    valid_timestamps.append(now)
    _memory_rate_limits[key] = valid_timestamps

    current_count = len(valid_timestamps)
    if current_count > max_attempts:
        return False, 0
    return True, max(0, max_attempts - current_count)

