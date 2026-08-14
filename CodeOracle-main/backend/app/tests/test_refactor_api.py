"""
Phase 7 API Integration Tests — /api/jobs/{job_id}/refactor/* endpoints.
"""
import io
import zipfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.refactor.schema import (
    RefactorResult, RiskSummary, BreakingChangeWarning, FileDiff, ValidationComparison
)

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


def test_refactor_api_404_missing_job():
    r = client.post("/api/jobs/missing-job-id-123/refactor/generate")
    assert r.status_code == 404


def test_generate_refactor_api_success():
    job_id = _upload_and_get_job_id()

    mock_result = RefactorResult(
        job_id=job_id,
        status="completed",
        total_files=1,
        files_modified=1,
        total_additions=2,
        total_deletions=1,
        risk_summary=RiskSummary(
            overall_risk="low",
            critical_warnings_count=0,
            high_warnings_count=0,
            medium_warnings_count=0,
            low_warnings_count=0,
            safety_score=100,
            recommendation="Safe modernization",
        ),
        files=[],
        all_warnings=[],
        all_opportunities=[],
    )

    with patch("app.api.refactor.refactoring_engine") as mock_engine:
        mock_engine.generate_refactor.return_value = mock_result
        r = client.post(f"/api/jobs/{job_id}/refactor/generate")

    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["risk_summary"]["safety_score"] == 100


def test_get_refactor_diffs_and_warnings():
    job_id = _upload_and_get_job_id()

    # Pre-populate refactor_result on the job
    mock_result = RefactorResult(
        job_id=job_id,
        status="completed",
        total_files=1,
        files_modified=1,
        total_additions=3,
        total_deletions=1,
        risk_summary=RiskSummary(
            overall_risk="medium",
            critical_warnings_count=0,
            high_warnings_count=0,
            medium_warnings_count=1,
            low_warnings_count=0,
            safety_score=95,
        ),
        files=[],
        all_warnings=[
            BreakingChangeWarning(
                severity="medium",
                category="return_type",
                file="calc.py",
                symbol="add",
                explanation="Type changed",
                suggested_mitigation="Review callers",
            )
        ],
        all_opportunities=[],
    )

    with patch("app.api.refactor.refactoring_engine") as mock_engine:
        mock_engine.generate_refactor.return_value = mock_result
        client.post(f"/api/jobs/{job_id}/refactor/generate")

    # Get warnings
    rw = client.get(f"/api/jobs/{job_id}/refactor/warnings")
    assert rw.status_code == 200
    warnings_data = rw.json()
    assert len(warnings_data["warnings"]) == 1
    assert warnings_data["warnings"][0]["symbol"] == "add"

    # Get diffs
    rd = client.get(f"/api/jobs/{job_id}/refactor/diffs")
    assert rd.status_code == 200


def test_refactor_validate_api():
    job_id = _upload_and_get_job_id()

    mock_val = ValidationComparison(
        status="verified",
        original_tests_passed=5,
        original_tests_failed=0,
        refactored_tests_passed=5,
        refactored_tests_failed=0,
        regressions=[],
        original_coverage_percent=70.0,
        refactored_coverage_percent=72.0,
        coverage_delta=2.0,
    )

    with patch("app.api.refactor.refactor_validator") as mock_validator:
        mock_validator.validate_refactor.return_value = mock_val
        r = client.post(f"/api/jobs/{job_id}/refactor/validate")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "verified"
    assert data["coverage_delta"] == 2.0
