"""
Refactor API — /api/jobs/{job_id}/refactor/*
Endpoints for generating modernization refactors, retrieving diffs and breaking change warnings,
and validating refactored code against existing test suites in an isolated Docker container or safe host sandbox.
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
from app.runners.schema import TestExecutionResult
from app.refactor.engine import refactoring_engine
from app.refactor.validator import refactor_validator
from app.ai.provider import (
    AIKeyMissingError,
    AIQuotaError,
    AITimeoutError,
    AIResponseError,
    AIServiceError,
)

logger = logging.getLogger("codeoracle.api.refactor")
router = APIRouter(prefix="/jobs", tags=["Refactoring"])


@router.post("/{job_id}/refactor/generate")
async def generate_refactor(job_id: str):
    """
    Analyzes legacy source files and generates proposed modernized code without modifying originals.
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/refactor/generate | Stage: refactor_generation | Job: {job_id}")
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

        result = refactoring_engine.generate_refactor(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "refactor_result", result.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/refactor/generate completed in {total_duration:.2f}s | Files Modified: {result.files_modified}")
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
        logger.exception(f"[FAILURE] Unexpected exception during refactoring generation for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal", "message": str(exc)}
        )


@router.get("/{job_id}/refactor")
async def get_refactor(job_id: str):
    """
    Returns latest generated refactor proposals, diffs, and risk summary.
    """
    logger.info(f"[ENDPOINT] GET /api/jobs/{job_id}/refactor")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    cached = job.get("refactor_result")
    if cached:
        return cached

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No refactor proposal found for job '{job_id}'. Run POST /api/jobs/{job_id}/refactor/generate first."
    )


@router.get("/{job_id}/refactor/diffs")
async def get_refactor_diffs(job_id: str):
    """
    Returns syntax-highlighted diffs and AST breaking change warnings.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    cached = job.get("refactor_result")
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No refactor proposal found for job '{job_id}'."
        )

    return {
        "job_id": job_id,
        "files_modified": cached.get("files_modified", 0),
        "diffs": [
            {
                "file_path": f.get("file_path"),
                "diff": f.get("diff"),
                "has_breaking_changes": f.get("has_breaking_changes", False),
                "breaking_change_warnings": f.get("breaking_change_warnings", []),
            }
            for f in cached.get("files", [])
        ],
        "risk_summary": cached.get("risk_summary", {}),
    }


@router.get("/{job_id}/refactor/warnings")
async def get_refactor_warnings(job_id: str):
    """
    Returns breaking change warnings and risk summary.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    cached = job.get("refactor_result") or {}
    return {
        "job_id": job_id,
        "warnings": cached.get("all_warnings", []),
        "risk_summary": cached.get("risk_summary", {}),
    }


@router.post("/{job_id}/refactor/validate")
async def validate_refactor(job_id: str):
    """
    Runs the generated test suite against the refactored code in the sandbox.
    Compares baseline test results against refactored test results.
    """
    t_start = time.perf_counter()
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/refactor/validate | Stage: refactor_validation | Job: {job_id}")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    stats = job.get("stats") or {}
    languages = stats.get("languages", ["python"])
    primary_lang = languages[0] if languages else "python"
    framework = "pytest" if primary_lang == "python" else "vitest"
    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    # Get baseline test results
    baseline_result = None
    if job.get("test_execution"):
        try:
            baseline_result = TestExecutionResult.model_validate(job["test_execution"])
        except Exception:
            pass

    try:
        comparison = refactor_validator.validate_refactor(
            job_dir=job_dir,
            language=primary_lang,
            framework=framework,
            baseline_result=baseline_result,
        )
        job_manager.save_job_field(job_id, "refactor_validation", comparison.model_dump())

        total_duration = time.perf_counter() - t_start
        logger.info(f"[PERF] POST /api/jobs/{job_id}/refactor/validate completed in {total_duration:.2f}s | Status: {comparison.status}")
        return comparison.model_dump()
    except Exception as exc:
        logger.exception(f"[FAILURE] Exception during refactor validation for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "validation_error", "message": str(exc)}
        )
