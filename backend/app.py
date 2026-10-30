"""FastAPI Application & Server Entry Point for Verism AI Backend.

Provides:
- Direct 'app' object export for ASGI web servers (uvicorn, gunicorn, cloud deployment)
- Standalone execution entrypoint via `python app.py`
"""

# Import the standard os module for filesystem operations and directory resolution
import os
# Import the sys module to manipulate module search paths
import sys

# Ensure backend root is on sys.path
# Prepend the absolute path of this file's parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the uvicorn ASGI server package
import uvicorn
# Import the main FastAPI application instance from app.main
from app.main import app
# Import application settings to retrieve default HOST, PORT, and DEBUG flags
from app.core.config import settings

# Expose app for `uvicorn app:app` or deployment platforms
# Define an alias named application pointing to app for WSGI/ASGI compatibility
application = app

# Check if script is run directly from the shell
if __name__ == "__main__":
    # Launch uvicorn web server
    uvicorn.run(
        # Specify module and application instance name
        "app:app",
        # Listen on configured host IP address (e.g. '0.0.0.0')
        host=settings.HOST,
        # Listen on configured TCP port number (e.g. 8000)
        port=settings.PORT,
        # Enable development hot-reloading if DEBUG setting is true
        reload=settings.DEBUG,
    )
