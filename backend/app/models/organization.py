# Module docstring explaining Organization multi-tenant database entity
"""Organization database model for multi-tenant institutional partitioning."""

# Import uuid library to generate unique random string identifiers
import uuid
# Import datetime and timezone utilities for UTC timestamping
from datetime import datetime, timezone
# Import SQLAlchemy Column, string, and timezone-aware datetime data types
from sqlalchemy import Column, String, DateTime
# Import ORM relationship utility
from sqlalchemy.orm import relationship

# Import declarative Base class from database configuration
from app.core.database import Base


# Database model representing an educational institution, university, or school organization
class Organization(Base):
    """Database model representing institutional tenant organizations.

    Provides top-level multi-tenant isolation grouping users, courses,
    curriculums, and policy configurations by institution.
    """

    # Specify target physical table name in PostgreSQL
    __tablename__ = "organizations"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Official legal name of the academic institution
    name = Column(String(255), nullable=False)
    # Primary email or web domain of the institution (e.g. 'stanford.edu')
    domain = Column(String(255), nullable=True, index=True)
    # URL-friendly slug identifier for vanity subdomains
    slug = Column(String(128), unique=True, nullable=False, index=True)
    # Timezone-aware UTC timestamp when organization record was created
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    # Timezone-aware UTC timestamp when organization record was last updated
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # One-to-many relationship linking all faculty and staff users belonging to this organization
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    # One-to-many relationship linking all courses hosted by this organization
    courses = relationship("Course", back_populates="organization", cascade="all, delete-orphan")

