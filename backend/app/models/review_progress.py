# Module docstring explaining ReviewProgress database model for persisting review queue state
"""ReviewProgress database model persisting educator navigation state across review sessions."""

# Import uuid library to generate cryptographically random unique primary keys
import uuid
# Import datetime and timezone primitives for timezone-aware UTC timestamps
from datetime import datetime, timezone
# Import SQLAlchemy primitives for columns, data types, integers, JSON, and foreign keys
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey
# Import ORM relationship utility for mapping related entities
from sqlalchemy.orm import relationship

# Import declarative Base class from app core database package
from app.core.database import Base


# Database model tracking review progress and last-viewed coordinates for educators
class ReviewProgress(Base):
    """Database model persisting teacher review session progress.

    Enables educators to resume multi-assignment review sessions without losing their
    filter configurations, sorting preferences, or last evaluated submission position.
    """

    # Specify physical table name in PostgreSQL
    __tablename__ = "review_progress"

    # Unique string identifier acting as primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Foreign key referencing educator user
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Scope classification (e.g. 'all', course_id, or assignment_id)
    scope_key = Column(String(128), nullable=False, index=True)
    # Identifier of last submission inspected in the review console
    last_viewed_submission_id = Column(String(64), nullable=True)
    # Active filter configuration serialized as JSON
    last_filters = Column(JSON, nullable=True)
    # Count of submissions approved or reviewed so far in this scope
    reviewed_count = Column(Integer, default=0, nullable=False)
    # Total count of submissions pending evaluation in this scope
    total_count = Column(Integer, default=0, nullable=False)
    # Timezone-aware UTC timestamp when progress was last updated
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    # Many-to-one relationship mapping the educator user
    user = relationship("User", backref="review_sessions")
