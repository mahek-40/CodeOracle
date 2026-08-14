"""
Phase 5 API Integration Tests — /api/jobs/{job_id}/tests/* endpoints.
"""
import io
import zipfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.runners.schema import (
    TestGenerationResult, GeneratedTestFile, TestExecutionResult
)
from app.ai.provider import AIKeyMissingError, AIQuotaError, AITimeoutError, AIServiceError

client = TestClient(app)


def _upload_and_get_job_id() -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("calc.py", "def add(a, b):\n    return a + b\n")
    buf.seek(0)
    r = client.post("/api/projects/upload",
                    files={"file": ("test.zip", buf, "application/zip")})
    assert r.status_code == 201
    return r.json()["job_id"]


# ─── Generate Tests API Tests ────────────────────────────────────────────────

def test_generate_tests_api_404_missing_job():
    r = client.post("/api/jobs/missing-job-id-xyz/tests/generate")
    assert r.status_code == 404


def test_generate_tests_api_success():
    job_id = _upload_and_get_job_id()
    mock_result = TestGenerationResult(
        job_id=job_id,
        status="completed",
        framework="pytest",
        total_files=1,
        generated_files=[
            GeneratedTestFile(
                path="generated_tests/test_calc.py",
                filename="test_calc.py",
                target_file="calc.py",
                language="python",
                content="def test_add(): assert add(1, 2) == 3",
                num_tests_estimated=1,
            )
        ],
    )
    with patch("app.api.tests.test_generator") as mock_gen:
        mock_gen.generate_tests.return_value = mock_result
        r = client.post(f"/api/jobs/{job_id}/tests/generate")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["framework"] == "pytest"
    assert len(data["generated_files"]) == 1
    assert data["generated_files"][0]["filename"] == "test_calc.py"


def test_generate_tests_api_key_missing_503():
    job_id = _upload_and_get_job_id()
    with patch("app.api.tests.test_generator") as mock_gen:
        mock_gen.generate_tests.side_effect = AIKeyMissingError()
        r = client.post(f"/api/jobs/{job_id}/tests/generate")
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "configuration"


def test_generate_tests_api_quota_429():
    job_id = _upload_and_get_job_id()
    with patch("app.api.tests.test_generator") as mock_gen:
        mock_gen.generate_tests.side_effect = AIQuotaError("quota exceeded")
        r = client.post(f"/api/jobs/{job_id}/tests/generate")
    assert r.status_code == 429
    assert r.json()["detail"]["error"] == "quota"


# ─── Run Tests API Tests ─────────────────────────────────────────────────────

def test_run_tests_api_404_missing_job():
    r = client.post("/api/jobs/missing-job-id-xyz/tests/run")
    assert r.status_code == 404


def test_run_tests_api_success():
    job_id = _upload_and_get_job_id()
    mock_execution = TestExecutionResult(
        job_id=job_id,
        status="passed",
        framework="pytest",
        sandboxed=True,
        exit_code=0,
        duration_ms=120,
        total_tests=3,
        passed_tests=3,
        failed_tests=0,
        skipped_tests=0,
        stdout="=== 3 passed in 0.12s ===",
        stderr="",
    )
    with patch("app.api.tests.docker_runner") as mock_runner:
        mock_runner.run_tests.return_value = mock_execution
        r = client.post(f"/api/jobs/{job_id}/tests/run")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "passed"
    assert data["passed_tests"] == 3
    assert data["sandboxed"] is True


# ─── Get Tests Status API Tests ──────────────────────────────────────────────

def test_get_tests_api():
    job_id = _upload_and_get_job_id()
    r = client.get(f"/api/jobs/{job_id}/tests")
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert "generation" in data
    assert "execution" in data
