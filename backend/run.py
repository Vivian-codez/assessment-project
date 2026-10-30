"""Server entry point for Verism AI FastAPI Backend."""

# Import the standard os module for filesystem path manipulation
import os
# Import the sys module to configure the Python runtime module search path
import sys

# Ensure backend directory is in sys.path
# Prepend the directory containing this run.py script to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the uvicorn ASGI web server runner
import uvicorn
# Import application configuration settings for HOST, PORT, and DEBUG
from app.core.config import settings

# Check if script is executed directly from command line
if __name__ == "__main__":
    # Start the uvicorn server running the FastAPI application
    uvicorn.run(
        # Specify target FastAPI instance using module path format
        "app.main:app",
        # Bind server to the configured host address
        host=settings.HOST,
        # Bind server to the configured port number
        port=settings.PORT,
        # Toggle auto-reload based on configured debug mode
        reload=settings.DEBUG,
    )
