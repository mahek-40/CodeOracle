"""
Refactor API — /api/jobs/{job_id}/refactor/*
Endpoints for generating modernization refactors, retrieving diffs and breaking change warnings,
and validating refactored code against existing test suites in an isolated Docker container.
"""
import os
import logging
import traceback
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
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
        graph = graph_builder.build(project_analysis)

        result = refactoring_engine.generate_refactor(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "refactor_result", result.model_dump())
        logger.info(f"[SUCCESS] POST /api/jobs/{job_id}/refactor/generate | Status: {result.status} | Files Modified: {result.files_modified}")
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

    refactor_data = job.get("refactor_result")
    if not refactor_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No refactor proposals generated yet for job '{job_id}'."
        )

    return refactor_data


@router.get("/{job_id}/refactor/warnings")
async def get_refactor_warnings(job_id: str):
    """
    Returns all detected breaking change warnings.
    """
    logger.info(f"[ENDPOINT] GET /api/jobs/{job_id}/refactor/warnings")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    refactor_data = job.get("refactor_result", {})
    return {"job_id": job_id, "warnings": refactor_data.get("all_warnings", [])}


@router.get("/{job_id}/refactor/diffs")
async def get_refactor_diffs(job_id: str):
    """
    Returns structured file diffs for all modified files.
    """
    logger.info(f"[ENDPOINT] GET /api/jobs/{job_id}/refactor/diffs")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    refactor_data = job.get("refactor_result", {})
    diffs = [f.get("diff") for f in refactor_data.get("files", []) if f.get("diff")]
    return {"job_id": job_id, "diffs": diffs}


@router.post("/{job_id}/refactor/validate")
async def validate_refactor(job_id: str):
    """
    Executes existing generated tests against the refactored code in the Docker sandbox.
    """
    logger.info(f"[ENDPOINT] POST /api/jobs/{job_id}/refactor/validate | Stage: refactor_validation | Job: {job_id}")
    job = job_manager.get_job(job_id)
    if not job:
        logger.warning(f"[FAILURE] Job '{job_id}' not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    stats = job.get("stats")
    if not stats:
        logger.warning(f"[FAILURE] Job '{job_id}' has no analysis stats")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis stats."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)
    project_analysis = ProjectAnalysis.model_validate(stats)

    orig_exec_data = job.get("test_execution")
    orig_exec = TestExecutionResult.model_validate(orig_exec_data) if orig_exec_data else None

    orig_cov_data = job.get("coverage_report")
    orig_cov = orig_cov_data.get("overall_coverage_percent") if orig_cov_data else None

    try:
        comparison = refactor_validator.validate_refactor(
            job_dir, project_analysis, orig_exec, orig_cov
        )
        job_manager.save_job_field(job_id, "refactor_validation", comparison.model_dump())
        job = job_manager.get_job(job_id)
        if job and "refactor_result" in job and isinstance(job["refactor_result"], dict):
            job["refactor_result"]["validation"] = comparison.model_dump()
            job_manager.save_job_field(job_id, "refactor_result", job["refactor_result"])

        logger.info(f"[SUCCESS] POST /api/jobs/{job_id}/refactor/validate | Status: {comparison.status} | Passed: {comparison.refactored_tests_passed}")
        return comparison.model_dump()

    except Exception as exc:
        logger.exception(f"[FAILURE] Exception during refactor validation for job {job_id}: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "validation_error", "message": str(exc)}
        )


@router.get("/{job_id}/refactor/validate")
async def get_refactor_validation(job_id: str):
    """
    Returns latest test validation comparison results.
    """
    logger.info(f"[ENDPOINT] GET /api/jobs/{job_id}/refactor/validate")
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    return {
        "job_id": job_id,
        "validation": job.get("refactor_validation"),
    }
