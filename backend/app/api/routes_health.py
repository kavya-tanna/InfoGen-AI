"""
api/routes_health.py
────────────────────
GET /api/health
"""
from fastapi import APIRouter
from app.config import settings
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get("/api/health")
async def health():
    """Health check endpoint."""
    provider = settings.effective_provider()
    return HealthResponse(
        status="healthy",
        provider=provider,
        demo_mode=settings.demo_mode or provider == "demo",
        model=settings.model_name,
        version="1.0.0",
    ).model_dump()
