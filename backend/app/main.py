"""
main.py
───────
FastAPI application entry point for InfoGen AI backend.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes_generate import router as generate_router
from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_jobs import router as jobs_router
from app.models import init_db
from app.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

    provider = settings.effective_provider()
    logger.info("=" * 60)
    logger.info("InfoGen AI Backend Starting")
    logger.info(f"  Provider : {provider}")
    logger.info(f"  Model    : {settings.model_name}")
    logger.info(f"  Demo Mode: {settings.demo_mode}")
    logger.info(f"  Docs     : http://127.0.0.1:8000/docs")
    logger.info(f"  Frontend : http://127.0.0.1:8000/")
    logger.info("=" * 60)
    yield


app = FastAPI(
    title="InfoGen AI",
    description="Gen AI Platform for Automated Content Transformation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID + Timing Middleware ───────────────────────────────────
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    logger.info(f"[{request_id}] {request.method} {request.url.path}")

    response = await call_next(request)

    elapsed = round((time.time() - start) * 1000, 1)
    logger.info(f"[{request_id}] {response.status_code} ({elapsed}ms)")

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed}ms"
    return response


# ── Include Routers ──────────────────────────────────────────────────
app.include_router(health_router, tags=["Health"])
app.include_router(generate_router, tags=["Generation"])
app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(jobs_router, tags=["Jobs"])


# ── Serve Frontend HTML ──────────────────────────────────────────────
FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "InfoGen_AI.html"


@app.get("/api/samples")
def demo_samples():
    import json
    return json.loads((FRONTEND_PATH.parent / "samples" / "demo.json").read_text(encoding="utf-8"))


@app.get("/")
async def serve_frontend():
    """Serve the InfoGen AI frontend."""
    if FRONTEND_PATH.exists():
        return FileResponse(FRONTEND_PATH, media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"message": "Frontend not found. Place InfoGen_AI.html in the project root."},
    )



