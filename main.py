"""Root ASGI application entry point for cloud deployments (Render, Railway, Fly.io).

Directly exposes `app` for:
- `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `uvicorn app:app`
- Standalone execution via `python main.py`
"""

# Import the standard os module for interacting with the operating system and reading environment variables
import os
# Import the sys module to manipulate the Python runtime module search path (sys.path)
import sys

# Ensure backend root is on sys.path
# Resolve the absolute path to the backend directory relative to this file's location
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
# Check if the resolved backend directory is already present in sys.path
if backend_dir not in sys.path:
    # Prepend the backend directory to sys.path so modules like app.main can be resolved
    sys.path.insert(0, backend_dir)

# Import the FastAPI application instance from app.main inside the backend package
from app.main import app

# Export app ASGI callable
# Define __all__ containing 'app' to clearly declare the public ASGI application interface
__all__ = ["app"]

# Check if this script is being executed directly from the terminal rather than imported
if __name__ == "__main__":
    # Import the uvicorn ASGI server library to serve HTTP requests
    import uvicorn

    # Read the PORT environment variable if set by cloud platforms, falling back to port 8000
    port = int(os.environ.get("PORT", 8000))
    # Run the uvicorn development/production server with the ASGI callable string
    uvicorn.run(
        # Specify module and application callable string format
        "main:app",
        # Listen on all network interfaces inside the container or host
        host="0.0.0.0",
        # Bind to the resolved port number
        port=port,
    )
