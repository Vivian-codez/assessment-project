# Module docstring explaining submissions router export
"""Submissions router export."""

# Import router instance from v1 submissions API module
from app.api.v1.submissions import router

# Export router symbol for external consumers
__all__ = ["router"]
