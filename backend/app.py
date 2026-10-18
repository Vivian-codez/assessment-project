"""FastAPI Application & Server Entry Point for Verism AI Backend.

Provides:
- Direct 'app' object export for ASGI web servers (uvicorn, gunicorn, cloud deployment)
- Standalone execution entrypoint via `python app.py`
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import uvicorn
from app.main import app
from app.core.config import settings

# Expose app for `uvicorn app:app` or deployment platforms
application = app

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
