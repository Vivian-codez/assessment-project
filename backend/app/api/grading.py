# Module docstring explaining grading router export
"""Grading and Review Queue router export."""

# Import router instance from v1 grading API module
from app.api.v1.grading import router

# Export router symbol for external consumers
__all__ = ["router"]
