"""
Tests API — /api/jobs/{job_id}/tests/*
Generates AI unit tests and executes them in an isolated Docker container.
"""
import os
import json
from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
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

router = APIRouter(prefix="/jobs", tags=["Tests"])


@router.post("/{job_id}/tests/generate")
async def generate_tests_for_job(job_id: str):
    """
    Generates runnable unit tests for an analysed project using Gemini.
    Tests are saved separately in {job_dir}/generated_tests/.
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

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)
        graph = graph_builder.build(project_analysis)

        result = test_generator.generate_tests(project_analysis, job_dir, graph)
        job_manager.save_job_field(job_id, "test_generation", result.model_dump())

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


@router.post("/{job_id}/tests/run")
async def run_tests_for_job(job_id: str):
    """
    Runs generated tests inside an isolated Docker sandbox container.
    Returns test counts, stdout, stderr, exit code, and execution duration.
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

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)
    stats = job.get("stats") or {}
    languages = stats.get("languages", ["python"])
    primary_lang = languages[0] if languages else "python"
    framework = "pytest" if primary_lang == "python" else "vitest"

    try:
        result = docker_runner.run_tests(job_dir, language=primary_lang, framework=framework)
        job_manager.save_job_field(job_id, "test_execution", result.model_dump())
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "runner_error", "message": str(exc)}
        )


@router.get("/{job_id}/tests")
async def get_job_tests(job_id: str):
    """
    Retrieves the generated test files and test execution results for a job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    job_dir = job.get("job_dir") or job_manager.get_job_dir(job_id)
    generation_data = job.get("test_generation")

    # Fallback to reading manifest from disk if present
    if not generation_data and job_dir:
        manifest_path = os.path.join(job_dir, "generated_tests", "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    generation_data = {
                        "job_id": job_id,
                        "status": "completed",
                        "framework": manifest.get("framework", "pytest"),
                        "total_files": len(manifest.get("files", [])),
                        "generated_files": manifest.get("files", []),
                    }
            except Exception:
                pass

    return {
        "job_id": job_id,
        "generation": generation_data,
        "execution": job.get("test_execution"),
    }
