import io
import zipfile
import json
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_deployment_health():
    """Verify health endpoint responds with 200 and valid JSON."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "CodeOracle"
    assert "environment" in data


def test_deployment_e2e_pipeline():
    """Simulate full end-to-end user workflow for deployment readiness."""
    # 1. Project Ingestion via ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "main.py",
            "def greet(name: str) -> str:\n    return f\"Hello, {name}!\"\n\ndef compute(a: int, b: int) -> int:\n    return a + b\n",
        )
        z.writestr(
            "helper.py",
            "from main import greet\n\ndef run():\n    return greet(\"World\")\n",
        )
    buf.seek(0)

    upload_res = client.post(
        "/api/projects/upload",
        files={"file": ("my_project.zip", buf.getvalue(), "application/zip")},
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    job_id = upload_data["job_id"]
    assert upload_data["status"] == "completed"
    assert upload_data["stats"]["total_lines"] > 0

    # 2. Status check
    job_res = client.get(f"/api/jobs/{job_id}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "completed"

    # 3. Dependency graph
    graph_res = client.get(f"/api/jobs/{job_id}/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert len(graph_data["nodes"]) >= 2
    assert len(graph_data["edges"]) >= 1

    # 4. Gemini explanation
    mock_file_ai = (
        '{"summary": "Test project for greetings", "purpose": "Demo project", "key_exports": ["greet"], '
        '"symbols": [{"name": "greet", "symbol_type": "function", "file_path": "main.py", "start_line": 1, '
        '"end_line": 2, "summary": "Greets user", "inputs": "name", "outputs": "str", "dependencies": []}]}'
    )
    with patch("app.ai.provider.GeminiProvider.generate", return_value=mock_file_ai):
        with patch("app.core.config.settings.GEMINI_API_KEY", "dummy_key"):
            explain_res = client.get(f"/api/jobs/{job_id}/explain")
            assert explain_res.status_code == 200
            assert len(explain_res.json()["files"]) >= 1

    # 5. Test generation and execution
    test_code = (
        "import pytest\nfrom main import greet, compute\n\n"
        "def test_greet():\n    assert greet('World') == 'Hello, World!'\n\n"
        "def test_compute():\n    assert compute(2, 3) == 5\n"
    )
    with patch("app.ai.provider.GeminiProvider.generate", return_value=f"```python\n{test_code}\n```"):
        with patch("app.core.config.settings.GEMINI_API_KEY", "dummy_key"):
            gen_res = client.post(f"/api/jobs/{job_id}/tests/generate")
            assert gen_res.status_code == 200
            assert len(gen_res.json()["generated_files"]) >= 1

            run_res = client.post(f"/api/jobs/{job_id}/tests/run")
            assert run_res.status_code == 200

            cov_res = client.get(f"/api/jobs/{job_id}/coverage")
            assert cov_res.status_code == 200

    # 6. Refactoring, warnings, and diffs
    refactor_code = (
        "def greet(name: str = 'Guest') -> str:\n    '''Return greeting message.'''\n    return f'Hello, {name}!'\n\n"
        "def compute(a: int, b: int) -> int:\n    '''Compute sum.'''\n    return a + b\n"
    )
    with patch("app.ai.provider.GeminiProvider.generate", return_value=f"```python\n{refactor_code}\n```"):
        with patch("app.core.config.settings.GEMINI_API_KEY", "dummy_key"):
            ref_res = client.post(f"/api/jobs/{job_id}/refactor/generate")
            assert ref_res.status_code == 200
            assert ref_res.json()["status"] in ["completed", "partial"]

            warn_res = client.get(f"/api/jobs/{job_id}/refactor/warnings")
            assert warn_res.status_code == 200

            diff_res = client.get(f"/api/jobs/{job_id}/refactor/diffs")
            assert diff_res.status_code == 200


def test_spa_routing_and_404_isolation():
    """Verify SPA index serving and strict 404 for unknown API endpoints."""
    # Root should serve 200
    root_res = client.get("/")
    assert root_res.status_code in [200, 404]  # 200 if frontend/dist built, 404 if not

    # API 404 should never return 200
    unknown_api = client.get("/api/unknown_endpoint_xyz")
    assert unknown_api.status_code == 404
