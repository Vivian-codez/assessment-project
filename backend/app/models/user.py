# Module docstring explaining local user account and session database entities
"""User and UserSession database models."""

# Import uuid library to generate cryptographically unique random identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy column, boolean, and data type primitives for table definitions
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from app.core.database to register ORM models
from app.core.database import Base


# Database model representing local user accounts for JWT authentication
class User(Base):
    """Database model representing local user accounts.

    Maintains faculty, administrator, and instructor profiles, credentials,
    tenant organization membership, and console preferences.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "users"

    # Alphanumeric unique user identifier acting as primary key
    id = Column(String(64), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    # Optional foreign key referencing parent institutional organization
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    # Full name of the user
    full_name = Column(String(255), nullable=True)
    # Full display name of the user (alias for full_name)
    name = Column(String(255), nullable=True)
    # Unique email address used for login authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    # User's academic role or faculty title
    role = Column(String(128), default="Instructor · Computer Science")
    # Bcrypt-hashed password string for identity verification
    hashed_password = Column(String(255), nullable=False)
    # Boolean flag tracking email verification status
    email_verified = Column(Boolean, default=False, nullable=False)
    # Cryptographic verification token sent via email confirmation
    verification_token = Column(String(255), nullable=True)
    # Cryptographic password reset token for account recovery
    password_reset_token = Column(String(255), nullable=True)
    # Timezone-aware UTC timestamp when password reset token expires
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    # JSON dictionary storing user preferences for console thresholds and display flags
    preferences = Column(JSON, default=lambda: {
        # Display matching context snippets alongside similarity percentages
        "show_similarity_context": True,
        # Require teacher justification notes when manually altering AI score suggestions
        "require_teacher_notes_on_overrides": False,
        # Display the AI content indicator probability flag
        "include_ai_content_indicator": True,
    })
    # UTC timestamp when user account was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # UTC timestamp when user profile was last updated
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    # Many-to-one relationship mapping the tenant organization
    organization = relationship("Organization", back_populates="users")
    # One-to-many relationship linking active refresh tokens
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    # One-to-many relationship linking courses managed by this user
    courses = relationship("Course", back_populates="teacher", foreign_keys="[Course.user_id]", cascade="all, delete-orphan")
    # One-to-many relationship linking assignment folders
    assignment_folders = relationship("AssignmentFolder", back_populates="user", cascade="all, delete-orphan")
    # One-to-many relationship linking monthly usage meters
    monthly_usages = relationship("MonthlyUsage", back_populates="user", cascade="all, delete-orphan")

    # Constructor method synchronizing full_name and legacy name keyword arguments
    def __init__(self, **kwargs):
        # Check if full_name was supplied but name was omitted
        if "full_name" in kwargs and "name" not in kwargs:
            # Mirror full_name value into name attribute for backward compatibility
            kwargs["name"] = kwargs["full_name"]
        # Check if name was supplied but full_name was omitted
        elif "name" in kwargs and "full_name" not in kwargs:
            # Mirror name value into full_name attribute
            kwargs["full_name"] = kwargs["name"]
        # Call base SQLAlchemy declarative class initializer with processed kwargs
        super().__init__(**kwargs)


# Database model representing active JWT authentication sessions and tokens
class UserSession(Base):
    """Database model tracking active user authentication sessions."""

    # Specify target physical table name in PostgreSQL
    __tablename__ = "user_sessions"

    # Unique alphanumeric identifier for the session
    id = Column(String(64), primary_key=True, index=True)
    # Foreign user identifier linking session to the authenticated User record
    user_id = Column(String(64), index=True, nullable=False)
    # JWT Bearer token string issued to the client
    token = Column(String(512), index=True, nullable=False)
    # Client browser user agent string for security verification
    user_agent = Column(String(512), nullable=True)
    # Client originating IP address for security logging
    ip_address = Column(String(64), nullable=True)
    # Absolute expiration timestamp after which the session token is revoked
    expires_at = Column(DateTime, nullable=False)
    # UTC timestamp when the session was initiated
    created_at = Column(DateTime, default=datetime.utcnow)
