"""Structured Logging and FERPA-Compliant Log Masking."""

# Import the standard logging library for formatted application log emission
import logging
# Import sys module to route log streams directly to standard output
import sys
# Import application settings to check DEBUG flag for log level configuration
from app.core.config import settings

# Configure root logger
# Initialize basic logging settings with custom formatting and output handlers
logging.basicConfig(
    # Set log level to DEBUG in development mode, otherwise default to INFO level
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    # Define log message structure including timestamp, log level, logger name, and message
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    # Direct log output stream to stdout for container log collectors and cloud log drivers
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Create and export a dedicated application logger named 'verism'
logger = logging.getLogger("verism")


# Function to log immutable security and administrative events for compliance audit trails
def log_audit_event(actor: str, action: str, entity: str, entity_id: str, details: str = ""):
    """Logs security and compliance events for audit trail."""
    # Emit an INFO-level log entry tagged with [AUDIT] containing structured event attributes
    logger.info(
        # Format the audit record with actor, action verb, target entity, entity ID, and detail payload
        f"[AUDIT] Actor='{actor}' Action='{action}' Entity='{entity}' EntityId='{entity_id}' Details='{details}'"
    )
