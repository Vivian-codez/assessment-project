# Module docstring explaining RefreshToken database entity for rotating sessions
"""RefreshToken database model for secure rotating session lifecycle."""

# Import uuid library to generate cryptographically unique random identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamp tracking
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, booleans, and foreign keys
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model storing hashed rotating refresh tokens for persistent authenticated sessions
class RefreshToken(Base):
    """Database model storing hashed rotating refresh tokens.

    Supports long-lived, multi-device sessions with cryptographic rotation,
    revocation on logout, and single-use invalidation.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "refresh_tokens"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing the authenticated user owning this refresh token
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Cryptographic SHA-256 hash of the issued refresh token string
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    # Timezone-aware UTC timestamp when this refresh token expires
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # Boolean flag indicating whether this refresh token has been explicitly revoked
    revoked = Column(Boolean, default=False, nullable=False)
    # Optional IP address of client issuing refresh token
    ip_address = Column(String(64), nullable=True)
    # Optional user-agent string of client device
    user_agent = Column(String(512), nullable=True)
    # Timezone-aware UTC timestamp recording when token was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the user owning this refresh token
    user = relationship("User", back_populates="refresh_tokens")

