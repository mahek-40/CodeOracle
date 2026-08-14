from datetime import datetime, timezone
import os
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for deployment monitoring and orchestrator liveness probes.
    Explicitly reports API and Gemini AI readiness.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    gemini_status = "ok" if bool(api_key) else "missing_api_key"

    return {
        "status": "ok",
        "api": "ok",
        "gemini": gemini_status,
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "gemini_configured": bool(api_key),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 0,
    }
