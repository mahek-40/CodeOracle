"""
Coverage API — /api/jobs/{job_id}/coverage/*
Measures real test coverage and runs targeted test improvement loops.
"""
import os
import time
import logging
import traceback
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.graph.schema import DependencyGraph
from app.analyzers.base.schema import ProjectAnalysis
from app.coverage.engine import coverage_engine
from app.ai.provider import (
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIResponseError,
    AIServiceError,
)

logger = logging.getLogger("codeoracle.api.coverage")
router = APIRouter(prefix="/jobs", tags=["Coverage"])


@router.post("/{job_id}/coverage/run")
async def run_job_coverage(job_id: str):
    """
    Executes existing tests in the Docker sandbox and measures real line coverage.
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/coverage/run | Stage: coverage_measurement | Job: {job_id}")
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
        logger.warning(f"[FAILURE] Job '{job_id}' has no analysis stats")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis stats."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)

        # Retrieve cached dependency graph or build
        if job.get("graph"):
            graph = DependencyGraph.model_validate(job["graph"])
        else:
            graph = graph_builder.build(project_analysis)
            job_manager.save_job_field(job_id, "graph", graph.model_dump())

        report = coverage_engine.measure_coverage(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "coverage_report", report.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/coverage/run completed in {total_duration:.2f}s | Overall: {report.overall_coverage_percent}%")
        return report.model_dump()

    except Exception as exc:
        logger.exception(f"[FAILURE] Exception during coverage run for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "coverage_measurement_error", "message": str(exc)}
        )


@router.post("/{job_id}/coverage/improve")
async def improve_job_coverage(job_id: str):
    """
    Runs iterative targeted test generation to improve line coverage toward >60%.
    Bounded to MAX_COVERAGE_RETRIES (3 retries).
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/coverage/improve | Stage: coverage_improvement | Job: {job_id}")
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
        logger.warning(f"[FAILURE] Job '{job_id}' has no analysis stats")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis stats."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)

        # Retrieve cached dependency graph or build
        if job.get("graph"):
            graph = DependencyGraph.model_validate(job["graph"])
        else:
            graph = graph_builder.build(project_analysis)
            job_manager.save_job_field(job_id, "graph", graph.model_dump())

        result = coverage_engine.improve_coverage(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "coverage_improvement", result.model_dump())
        if result.latest_report:
            job_manager.save_job_field(job_id, "coverage_report", result.latest_report.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/coverage/improve completed in {total_duration:.2f}s | {result.initial_coverage}% -> {result.final_coverage}%")
        return result.model_dump()

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
        logger.exception(f"[FAILURE] Exception during coverage improve for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "coverage_improvement_error", "message": str(exc)}
        )


@router.get("/{job_id}/coverage")
async def get_job_coverage(job_id: str):
    """
    Returns the latest measured coverage report and improvement results for a job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    return {
        "job_id": job_id,
        "report": job.get("coverage_report"),
        "improvement": job.get("coverage_improvement"),
    }
