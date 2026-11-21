# Module docstring explaining rubrics router export
"""Rubrics router export."""

# Import router instance from v1 rubrics API module
from app.api.v1.rubrics import router

# Export router symbol for external consumers
__all__ = ["router"]
