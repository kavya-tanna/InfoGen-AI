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
    result = HealthResponse(
        status="healthy",
        provider=provider,
        demo_mode=settings.demo_mode or provider == "demo",
        model="extractive-v1" if provider == "demo" else settings.model_name,
        version="1.0.0",
    ).model_dump()
    result["configuration_notice"] = settings.configuration_error()
    result["fallback_provider"] = settings.fallback_provider if settings.google_api_key and provider != "demo" else ""
    result["fallback_model"] = settings.gemini_model_name if result["fallback_provider"] else ""
    return result
