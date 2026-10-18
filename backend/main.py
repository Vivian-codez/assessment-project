"""FastAPI ASGI application entry point for Render and Cloud Deployments.

Exposes `app` directly for:
- `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `gunicorn -k uvicorn.workers.UvicornWorker main:app`
- Standalone execution via `python main.py`
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.core.config import settings

# Export app ASGI callable for uvicorn/gunicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
    )
