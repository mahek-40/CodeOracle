"""
Phase 6 API Integration Tests — /api/jobs/{job_id}/coverage/* endpoints.
"""
import io
import zipfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.coverage.schema import CoverageReport, FileCoverage, CoverageImprovementResult

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


def test_coverage_run_api_404_missing_job():
    r = client.post("/api/jobs/nonexistent-id-xyz/coverage/run")
    assert r.status_code == 404


def test_coverage_run_api_success():
    job_id = _upload_and_get_job_id()
    mock_report = CoverageReport(
        job_id=job_id,
        language="python",
        total_lines=5,
        total_covered_lines=4,
        total_uncovered_lines=1,
        overall_coverage_percent=80.0,
        target_reached=True,
        files=[
            FileCoverage(
                path="calc.py",
                language="python",
                total_lines=5,
                covered_lines_count=4,
                uncovered_lines_count=1,
                coverage_percent=80.0,
            )
        ]
    )

    with patch("app.api.coverage.coverage_engine") as mock_engine:
        mock_engine.measure_coverage.return_value = mock_report
        r = client.post(f"/api/jobs/{job_id}/coverage/run")

    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert data["overall_coverage_percent"] == 80.0
    assert data["target_reached"] is True


def test_coverage_improve_api_success():
    job_id = _upload_and_get_job_id()
    mock_result = CoverageImprovementResult(
        job_id=job_id,
        initial_coverage=45.0,
        final_coverage=75.0,
        coverage_gain=30.0,
        target_reached=True,
        status="target_reached",
        total_iterations=2,
        iterations=[],
        latest_report=None,
    )

    with patch("app.api.coverage.coverage_engine") as mock_engine:
        mock_engine.improve_coverage.return_value = mock_result
        r = client.post(f"/api/jobs/{job_id}/coverage/improve")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "target_reached"
    assert data["final_coverage"] == 75.0
    assert data["coverage_gain"] == 30.0


def test_get_coverage_api():
    job_id = _upload_and_get_job_id()
    r = client.get(f"/api/jobs/{job_id}/coverage")
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert "report" in data
    assert "improvement" in data
