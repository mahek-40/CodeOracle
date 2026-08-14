"""
Coverage API — /api/jobs/{job_id}/coverage/*
Measures real test coverage and runs targeted test improvement loops.
"""
import os
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.analyzers.base.schema import ProjectAnalysis
from app.coverage.engine import coverage_engine
from app.ai.provider import (
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIResponseError,
    AIServiceError,
)

router = APIRouter(prefix="/jobs", tags=["Coverage"])


@router.post("/{job_id}/coverage/run")
async def run_job_coverage(job_id: str):
    """
    Executes existing tests in the Docker sandbox and measures real line coverage.
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
            detail=f"Job '{job_id}' has no analysis stats."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)
        graph = graph_builder.build(project_analysis)

        report = coverage_engine.measure_coverage(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "coverage_report", report.model_dump())
        return report.model_dump()

    except Exception as exc:
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
            detail=f"Job '{job_id}' has no analysis stats."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)
        graph = graph_builder.build(project_analysis)

        result = coverage_engine.improve_coverage(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "coverage_improvement", result.model_dump())
        if result.latest_report:
            job_manager.save_job_field(job_id, "coverage_report", result.latest_report.model_dump())

        return result.model_dump()

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


@router.get("/{job_id}/coverage")
async def get_job_coverage(job_id: str):
    """
    Returns latest coverage summary, per-file line breakdown, and iteration history.
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
