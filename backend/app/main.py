import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import applications, documents, jobs, profile

logger = logging.getLogger("vrutti")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Vrutti API",
    description="Backend for Vrutti, a personal AI job application agent.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next):
    """Any exception that isn't already an HTTPException would otherwise
    reach Starlette's ServerErrorMiddleware, which sits *outside* CORSMiddleware
    in the stack — so its response never gets CORS headers attached, and the
    browser reports it to the frontend as an opaque "Failed to fetch" instead
    of a readable error. Catching it here, in middleware declared before
    CORSMiddleware is added (Starlette's add_middleware prepends, so the
    later-added CORSMiddleware ends up wrapping this one), keeps the response
    inside CORS's reach. The real traceback still goes to Vercel's function
    logs for debugging.
    """
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": f"Something went wrong on the server: {exc}"},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(documents.router)
app.include_router(applications.router)
