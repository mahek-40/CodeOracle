"""
Explanation API — GET /api/jobs/{job_id}/explain
Returns hierarchical Gemini-powered explanation for a completed job.
The API key never leaves the backend.
"""
import logging
import traceback
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

logger = logging.getLogger("codeoracle.api.explain")
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
    logger.info(f"[ENDPOINT] GET /api/jobs/{job_id}/explain | Stage: explanation_generation | Job: {job_id}")
    job = job_manager.get_job(job_id)
    if not job:
        logger.warning(f"[FAILURE] Job '{job_id}' not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    if job.get("status") != "completed":
        logger.warning(f"[FAILURE] Job '{job_id}' is not yet completed (status: {job.get('status')})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not yet completed (status: {job.get('status')})."
        )

    stats = job.get("stats")
    if not stats:
        logger.warning(f"[FAILURE] Job '{job_id}' has no analysis data")
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
        job_manager.save_job_field(job_id, "explanation", explanation.model_dump())
        logger.info(f"[SUCCESS] GET /api/jobs/{job_id}/explain | Overview length: {len(explanation.overview)} | Files explained: {len(explanation.files)}")
        return explanation.model_dump()

    except AIKeyMissingError as exc:
        logger.error(f"[FAILURE] AIKeyMissingError for job {job_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "configuration", "message": exc.message}
        )
    except AIQuotaError as exc:
        logger.error(f"[FAILURE] AIQuotaError for job {job_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "quota", "message": exc.message}
        )
    except AITimeoutError as exc:
        logger.error(f"[FAILURE] AITimeoutError for job {job_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error": "timeout", "message": exc.message}
        )
    except (AIResponseError, AIServiceError) as exc:
        logger.error(f"[FAILURE] AIServiceError for job {job_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ai_service", "message": exc.message}
        )
    except Exception as exc:
        logger.exception(f"[FAILURE] Unexpected exception during explanation generation for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal", "message": str(exc)}
        )
