from datetime import datetime, timezone
import os
from fastapi import APIRouter
from app.core.config import settings
from app.ai.provider import gemini_provider

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for deployment monitoring and orchestrator liveness probes.
    Explicitly reports API, Gemini AI readiness, and selected Gemini model.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    gemini_status = "ok" if bool(api_key) else "missing_api_key"
    selected_model = gemini_provider.MODEL_NAME if bool(api_key) else None

    return {
        "status": "ok",
        "api": "ok",
        "gemini": gemini_status,
        "selected_model": selected_model,
        "gemini_model": selected_model,
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "gemini_configured": bool(api_key),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 0,
    }
