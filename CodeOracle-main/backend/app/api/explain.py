"""
Explanation API — GET /api/jobs/{job_id}/explain
Returns hierarchical Gemini-powered explanation for a completed job.
The API key never leaves the backend.
"""
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.analyzers.base.schema import ProjectAnalysis
from app.ai.engine import explanation_engine
from app.ai.provider import (
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIResponseError,
    AIServiceError,
)

router = APIRouter(prefix="/jobs", tags=["Explanation"])


@router.get("/{job_id}/explain")
async def explain_job(job_id: str):
    """
    Generates a hierarchical, Gemini-powered explanation for an analysed project.
    - Requires GEMINI_API_KEY environment variable.
    - Never sends the full repository in one prompt.
    - Returns partial results if individual files fail.
    - Returns structured error messages for all AI failure modes.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not yet completed (status: {job.get('status')})."
        )

    stats = job.get("stats")
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis data."
        )

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)

        # Build dependency graph for context enrichment
        graph = graph_builder.build(project_analysis)

        # Generate hierarchical explanation
        explanation = explanation_engine.explain_project(project_analysis, graph)
        return explanation.model_dump()

    except AIKeyMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "configuration", "message": exc.message}
        )
    except AIQuotaError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "quota", "message": exc.message}
        )
    except AITimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": "timeout", "message": exc.message}
        )
    except (AIResponseError, AIServiceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_service", "message": exc.message}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal", "message": str(exc)}
        )
