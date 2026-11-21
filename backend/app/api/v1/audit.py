# Module docstring explaining Audit Log API endpoints for FERPA/GDPR compliance
"""Audit Log API endpoints for FERPA/GDPR compliance inspection."""

# Import List generic type annotation from typing module
from typing import List
# Import FastAPI components for routing, dependency injection, and query parameters
from fastapi import APIRouter, Depends, Query
# Import Session from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import get_db dependency providing an active database session
from app.core.database import get_db
# Import AuditLog database model
from app.models.audit_log import AuditLog

# Initialize FastAPI router instance with /audit-logs prefix and Audit & Compliance tag
router = APIRouter(prefix="/audit-logs", tags=["Audit & Compliance"])


# HTTP GET route handler returning chronological audit trail records
@router.get("")
def get_audit_logs(
    # Query parameter specifying maximum records to retrieve (defaults to 50, maximum 200)
    limit: int = Query(50, le=200),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing audit trail inspection
    """Retrieve immutable audit trail records for grade stamps, overrides, and PII access."""
    # Query audit logs ordered by creation timestamp descending up to limit
    logs = (
        # Query AuditLog table
        db.query(AuditLog)
        # Order by created_at descending for chronological recency
        .order_by(AuditLog.created_at.desc())
        # Cap results by limit parameter
        .limit(limit)
        # Retrieve all matching rows
        .all()
    )
    # Serialize audit log records into list of response dictionaries
    return [
        # Construct audit log representation dictionary
        {
            # Set unique audit record ID
            "id": log.id,
            # Set actor name or user identifier who performed action
            "actor": log.actor_name,
            # Set action name string (e.g. STAMP_GRADE, OVERRIDE_SCORE)
            "action": log.action,
            # Set target entity category type (e.g. Submission, Student)
            "entity_type": log.entity_type,
            # Set target entity identifier
            "entity_id": log.entity_id,
            # Set JSON details payload capturing changed attributes
            "details": log.details,
            # Set UTC timestamp when action was audited
            "timestamp": log.created_at,
        }
        # Iterate over each queried log record
        for log in logs
    ]
