"""Audit Log API endpoints for FERPA/GDPR compliance inspection."""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit & Compliance"])


@router.get("")
def get_audit_logs(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve immutable audit trail records for grade stamps, overrides, and PII access."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "actor": log.actor_name,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
            "timestamp": log.created_at,
        }
        for log in logs
    ]
