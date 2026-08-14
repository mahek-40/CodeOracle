"""
Explanation API — GET /api/jobs/{job_id}/explain
Returns hierarchical Gemini-powered explanation for a completed job.
Features response caching, timing logs, and graceful error handling.
"""
import time
import logging
import traceback
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.analyzers.base.schema import ProjectAnalysis
from app.graph.schema import DependencyGraph
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
async def explain_job(job_id: str, force_refresh: bool = False):
    """
    Generates a hierarchical, Gemini-powered explanation for an analysed project.
    - Requires GEMINI_API_KEY environment variable.
    - Uses cached explanation when available (<1ms) unless force_refresh=True.
    - Returns partial results if individual files fail.
    - Returns structured error messages for all AI failure modes.
    """
    t_start = time.perf_counter()
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

    # Check cached explanation
    if not force_refresh and job.get("explanation"):
        logger.info(f"[PERF] Returning cached explanation for job {job_id} in {time.perf_counter() - t_start:.2f}s")
        return job["explanation"]

    stats = job.get("stats")
    if not stats:
        logger.warning(f"[FAILURE] Job '{job_id}' has no analysis data")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis data."
        )

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)

        # Retrieve cached dependency graph or build
        if job.get("graph"):
            graph = DependencyGraph.model_validate(job["graph"])
        else:
            graph = graph_builder.build(project_analysis)
            job_manager.save_job_field(job_id, "graph", graph.model_dump())

        # Generate hierarchical explanation
        explanation = explanation_engine.explain_project(project_analysis, graph)
        job_manager.save_job_field(job_id, "explanation", explanation.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] GET /api/jobs/{job_id}/explain completed in {total_duration:.2f}s | Files: {len(explanation.files)}")
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
