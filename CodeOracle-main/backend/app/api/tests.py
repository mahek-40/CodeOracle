"""
Tests API — /api/jobs/{job_id}/tests/*
Generates AI unit tests and executes them in an isolated Docker container or host sandbox.
"""
import os
import json
import time
import logging
import traceback
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.graph.schema import DependencyGraph
from app.analyzers.base.schema import ProjectAnalysis
from app.runners.test_generator import test_generator
from app.runners.docker_runner import docker_runner
from app.ai.provider import (
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIResponseError,
    AIServiceError,
)

logger = logging.getLogger("codeoracle.api.tests")
router = APIRouter(prefix="/jobs", tags=["Tests"])


@router.post("/{job_id}/tests/generate")
async def generate_tests_for_job(job_id: str):
    """
    Generates runnable unit tests for an analysed project using Gemini.
    Tests are saved separately in {job_dir}/generated_tests/.
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/tests/generate | Stage: test_generation | Job: {job_id}")
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

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)

        # Retrieve cached dependency graph or build
        if job.get("graph"):
            graph = DependencyGraph.model_validate(job["graph"])
        else:
            graph = graph_builder.build(project_analysis)
            job_manager.save_job_field(job_id, "graph", graph.model_dump())

        result = test_generator.generate_tests(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "test_generation", result.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/tests/generate completed in {total_duration:.2f}s | Files: {len(result.generated_files)}")
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
        logger.exception(f"[FAILURE] Unexpected exception during test generation for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal", "message": str(exc)}
        )


@router.post("/{job_id}/tests/run")
async def run_tests_for_job(job_id: str):
    """
    Runs generated tests inside an isolated Docker sandbox container or safe subprocess fallback.
    Returns test counts, stdout, stderr, exit code, and execution duration.
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/tests/run | Stage: test_execution | Job: {job_id}")
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

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)
    stats = job.get("stats") or {}
    languages = stats.get("languages", ["python"])
    primary_lang = languages[0] if languages else "python"
    framework = "pytest" if primary_lang == "python" else "vitest"

    try:
        result = docker_runner.run_tests(job_dir, language=primary_lang, framework=framework)
        job_manager.save_job_field(job_id, "test_execution", result.model_dump())
        if result.coverage_report:
            job_manager.save_job_field(job_id, "coverage_report", result.coverage_report.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/tests/run completed in {total_duration:.2f}s | Passed: {result.passed_tests}/{result.total_tests}")
        return result.model_dump()
    except Exception as exc:
        logger.exception(f"[FAILURE] Exception during test execution for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "runner_error", "message": str(exc)}
        )


@router.get("/{job_id}/tests")
async def get_job_tests(job_id: str):
    """
    Returns test generation and execution metadata for a job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    return {
        "job_id": job_id,
        "generation": job.get("test_generation"),
        "execution": job.get("test_execution"),
    }
