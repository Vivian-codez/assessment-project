"""Server runner delegating to centralized main ASGI entrypoint."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import app, application
from app.core.config import settings

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("main:app", host=settings.HOST, port=port, reload=settings.DEBUG)
