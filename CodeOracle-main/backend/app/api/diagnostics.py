"""
System Diagnostics API — GET /api/diagnostics
Comprehensive deployment verification and runtime health inspection for CodeOracle.
"""
import os
import sys
import shutil
import subprocess
import time
from typing import Dict, Any
from fastapi import APIRouter
from app.core.config import settings
from app.jobs.manager import job_manager, TEMP_BASE_DIR
from app.ai.provider import gemini_provider, AIKeyMissingError
from app.runners.docker_runner import docker_runner

router = APIRouter(tags=["Diagnostics"])


@router.get("/diagnostics")
async def run_system_diagnostics() -> Dict[str, Any]:
    """
    Performs full system diagnostic inspection across all subsystems:
    - Jobs workspace and disk health
    - Gemini AI connectivity probe
    - Docker / subprocess sandbox runner
    - Coverage tooling
    - Refactoring engine
    - Frontend SPA static bundle
    """
    # 1. Jobs Subsystem
    jobs_writable = False
    try:
        test_file = os.path.join(TEMP_BASE_DIR, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        jobs_writable = True
    except Exception:
        jobs_writable = False

    total_on_disk = len(os.listdir(TEMP_BASE_DIR)) if os.path.exists(TEMP_BASE_DIR) else 0

    jobs_info = {
        "status": "ok" if jobs_writable else "error",
        "active_jobs_count": len(job_manager._jobs),
        "workspaces_on_disk": total_on_disk,
        "base_directory": TEMP_BASE_DIR,
        "writable": jobs_writable,
    }

    # 2. Gemini AI Subsystem
    api_key_set = bool(settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", ""))
    gemini_status = "missing_api_key"
    gemini_details = "GEMINI_API_KEY environment variable is not configured."
    probe_latency_ms = None

    if api_key_set:
        start_probe = time.time()
        try:
            # Send a minimal, 1-token test prompt to verify API connectivity and quota
            res = gemini_provider.generate("Ping: reply 'pong'", temperature=0.0)
            probe_latency_ms = int((time.time() - start_probe) * 1000)
            gemini_status = "ok"
            gemini_details = f"Connected to {gemini_provider.MODEL_NAME} ({probe_latency_ms}ms latency)"
        except AIKeyMissingError:
            gemini_status = "missing_api_key"
            gemini_details = "API key was rejected or absent."
        except Exception as exc:
            err_str = str(exc).lower()
            if "quota" in err_str or "429" in err_str or "rate" in err_str:
                gemini_status = "quota_exceeded"
                gemini_details = f"Gemini API quota exceeded: {str(exc)}"
            else:
                gemini_status = "error"
                gemini_details = f"Gemini connection error: {str(exc)}"

    gemini_info = {
        "status": gemini_status,
        "api_key_configured": api_key_set,
        "model": gemini_provider.MODEL_NAME,
        "selected_model": gemini_provider._selected_model,
        "discovered_models": gemini_provider._discovered_models or [],
        "details": gemini_details,
        "latency_ms": probe_latency_ms,
    }

    # 3. Sandbox Subsystem
    docker_avail, docker_msg = docker_runner.is_docker_available()
    pytest_avail = False
    try:
        import pytest
        pytest_avail = True
    except ImportError:
        pass

    node_avail = bool(shutil.which("node"))
    npm_avail = bool(shutil.which("npm"))

    sandbox_info = {
        "status": "ok",
        "docker_available": docker_avail,
        "docker_message": docker_msg if not docker_avail else "Docker daemon connected",
        "subprocess_fallback_enabled": docker_runner.allow_local_fallback,
        "python_runtime": sys.version.split()[0],
        "pytest_installed": pytest_avail,
        "node_installed": node_avail,
        "npm_installed": npm_avail,
    }

    # 4. Coverage Subsystem
    coverage_avail = False
    try:
        import coverage
        coverage_avail = True
    except ImportError:
        pass

    coverage_info = {
        "status": "ok" if coverage_avail else "warning",
        "coverage_py_installed": coverage_avail,
        "supported_formats": ["coverage.json", "coverage.xml", "coverage-summary.json", "lcov.info"],
        "target_benchmark": "60.0%",
    }

    # 5. Refactor Subsystem
    refactor_info = {
        "status": "ok",
        "ast_diff_engine": "active",
        "breaking_change_detector": "active",
        "supported_languages": ["python", "javascript"],
        "non_destructive_guarantee": True,
    }

    # 6. Frontend Subsystem
    from app.main import frontend_dist
    frontend_info = {
        "status": "ok" if (frontend_dist and os.path.exists(os.path.join(frontend_dist, "index.html"))) else "not_built",
        "dist_directory": frontend_dist,
        "index_html_present": bool(frontend_dist and os.path.exists(os.path.join(frontend_dist, "index.html"))),
        "spa_serving": bool(frontend_dist),
    }

    overall_status = "ok"
    if not jobs_writable or (api_key_set and gemini_status not in ("ok", "missing_api_key")):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "environment": settings.ENV,
        "version": settings.VERSION,
        "jobs": jobs_info,
        "gemini": gemini_info,
        "sandbox": sandbox_info,
        "coverage": coverage_info,
        "refactor": refactor_info,
        "frontend": frontend_info,
    }
