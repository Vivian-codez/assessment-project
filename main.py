"""Root ASGI application entry point for cloud deployments (Render, Railway, Fly.io).

Directly exposes `app` for:
- `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `uvicorn app:app`
- Standalone execution via `python main.py`
"""

import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Export app ASGI callable
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
    )
