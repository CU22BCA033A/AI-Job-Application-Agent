"""Vercel Python serverless entrypoint.

Vercel auto-detects any ASGI/WSGI app exported as `app` from a file under
`api/`, so this file just re-exports the real FastAPI app from app.main —
same code path as running `uvicorn app.main:app` locally.
"""

from app.main import app

__all__ = ["app"]
