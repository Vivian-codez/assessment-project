# Module docstring explaining jobs router export
"""Jobs and background worker tasks router export."""

# Import router instance from v1 jobs API module
from app.api.v1.jobs import router

# Export router symbol for external consumers
__all__ = ["router"]
