"""
Tests for System Diagnostics API (/api/diagnostics) and Health API (/api/health).
"""
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_health_endpoint_contract():
    """Verify GET /api/health reports status, api, gemini, and environment."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["api"] == "ok"
    assert "gemini" in data
    assert data["gemini"] in ("ok", "missing_api_key", "quota_exceeded")
    assert "gemini_configured" in data


def test_root_health_endpoint_contract():
    """Verify GET /health reports status, api, and gemini."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["api"] == "ok"
    assert "gemini" in data


def test_diagnostics_endpoint_contract():
    """Verify GET /api/diagnostics returns complete subsystems health dictionary."""
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    data = resp.json()

    # Subsystems verification
    assert "status" in data
    assert "jobs" in data
    assert "gemini" in data
    assert "sandbox" in data
    assert "coverage" in data
    assert "refactor" in data
    assert "frontend" in data

    # Jobs subsystem details
    jobs = data["jobs"]
    assert "active_jobs_count" in jobs
    assert "workspaces_on_disk" in jobs
    assert "writable" in jobs
    assert jobs["writable"] is True

    # Sandbox subsystem details
    sandbox = data["sandbox"]
    assert "docker_available" in sandbox
    assert "subprocess_fallback_enabled" in sandbox
    assert sandbox["subprocess_fallback_enabled"] is True
    assert "python_runtime" in sandbox

    # Coverage subsystem details
    coverage = data["coverage"]
    assert "supported_formats" in coverage
    assert "target_benchmark" in coverage
    assert coverage["target_benchmark"] == "60.0%"

    # Refactor subsystem details
    refactor = data["refactor"]
    assert refactor["non_destructive_guarantee"] is True
    assert "python" in refactor["supported_languages"]
    assert "javascript" in refactor["supported_languages"]
