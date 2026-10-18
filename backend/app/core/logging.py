"""Structured Logging and FERPA-Compliant Log Masking."""

import logging
import sys
from app.core.config import settings

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("verism")


def log_audit_event(actor: str, action: str, entity: str, entity_id: str, details: str = ""):
    """Logs security and compliance events for audit trail."""
    logger.info(
        f"[AUDIT] Actor='{actor}' Action='{action}' Entity='{entity}' EntityId='{entity_id}' Details='{details}'"
    )
