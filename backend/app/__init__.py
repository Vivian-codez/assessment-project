# Package docstring explaining Verism AI Backend Application
"""Verism AI Backend Application Package."""

# Import the core FastAPI application instance from app.main
from app.main import app

# Specify backend application semantic release version string
__version__ = "1.0.0"
# Export app instance for WSGI/ASGI servers
__all__ = ["app"]
