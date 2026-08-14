from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for deployment monitoring and orchestrator liveness probes.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 0
    }
