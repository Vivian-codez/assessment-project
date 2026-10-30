"""FastAPI ASGI application entry point for Render and Cloud Deployments.

Exposes `app` directly for:
- `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `gunicorn -k uvicorn.workers.UvicornWorker main:app`
- Standalone execution via `python main.py`
"""

# Import the standard os module for interacting with system environment variables and path resolution
import os
# Import the sys module to configure the module resolution search path
import sys

# Ensure backend root is on sys.path
# Prepend the directory containing this script to sys.path so the 'app' package can be imported directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the FastAPI application instance from the app.main module
from app.main import app
# Import the centralized application settings instance to read port and debug preferences
from app.core.config import settings

# Export app ASGI callable for uvicorn/gunicorn
# Declare the public ASGI interface for WSGI/ASGI application servers
__all__ = ["app"]

# Check if this script is being executed directly rather than imported as a library
if __name__ == "__main__":
    # Import the uvicorn ASGI web server library
    import uvicorn

    # Resolve the port number from the PORT environment variable, falling back to configured settings.PORT
    port = int(os.environ.get("PORT", settings.PORT))
    # Start the uvicorn server with the specified configuration
    uvicorn.run(
        # Pass the import string pointing to the FastAPI app instance
        "main:app",
        # Listen on all IPv4 addresses (all network interfaces)
        host="0.0.0.0",
        # Bind the HTTP listener to the resolved port
        port=port,
        # Enable auto-reload on code changes if settings.DEBUG is true
        reload=settings.DEBUG,
    )
