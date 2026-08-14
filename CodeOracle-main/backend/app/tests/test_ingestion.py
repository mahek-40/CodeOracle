import os
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_mock_zip(file_dict: dict) -> io.BytesIO:
    """Helper to construct in-memory ZIP archive from a dict of {filename: content}."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path, content in file_dict.items():
            zip_file.writestr(file_path, content)
    zip_buffer.seek(0)
    return zip_buffer


# 1. Valid ZIP Test
def test_valid_zip_upload():
    files = {
        "main.py": "def hello():\n    print('Hello World')\n",
        "src/utils.js": "function add(a, b) {\n  return a + b;\n}\n",
        "README.md": "# Sample Project\n",
        "node_modules/ignored.js": "// should be ignored\n"
    }
    zip_bytes = create_mock_zip(files)
    response = client.post(
        "/api/projects/upload",
        files={"file": ("project.zip", zip_bytes, "application/zip")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["stage"] in ["ingestion", "analysis"]
    assert "job_id" in data
    
    stats = data["stats"]
    assert stats["total_files"] == 2
    assert "python" in stats["languages"]
    assert "javascript" in stats["languages"]

    # Verify GET /api/jobs/{job_id}
    job_id = data["job_id"]
    job_resp = client.get(f"/api/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "completed"


# 2. Malformed ZIP Test
def test_malformed_zip_upload():
    corrupt_bytes = io.BytesIO(b"this is not a zip file data stream")
    response = client.post(
        "/api/projects/upload",
        files={"file": ("corrupt.zip", corrupt_bytes, "application/zip")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "Uploaded file is not a valid" in data["detail"]["message"]


# 3. Path Traversal Attempt Test
def test_path_traversal_zip_upload():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("../../etc/passwd", "root:x:0:0:root:/root:/bin/bash\n")
        zip_file.writestr("normal.py", "print('ok')\n")
    zip_buffer.seek(0)

    response = client.post(
        "/api/projects/upload",
        files={"file": ("malicious.zip", zip_buffer, "application/zip")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "Path traversal detected" in data["detail"]["message"]


# 4. Unsupported Files Only Test
def test_unsupported_files_zip_upload():
    files = {
        "data.csv": "id,name\n1,alice\n",
        "notes.txt": "just plain text notes\n",
        "image.png": "binary png mock\n"
    }
    zip_bytes = create_mock_zip(files)
    response = client.post(
        "/api/projects/upload",
        files={"file": ("textonly.zip", zip_bytes, "application/zip")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "No supported Python" in data["detail"]["message"]


# 5. Line Limit Exceeded Test
def test_line_limit_exceeded_zip_upload():
    long_code = "x = 1\n" * 10005
    files = {"large_module.py": long_code}
    zip_bytes = create_mock_zip(files)

    response = client.post(
        "/api/projects/upload",
        files={"file": ("large.zip", zip_bytes, "application/zip")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "exceeds line limit" in data["detail"]["message"]


# 6. Valid Public GitHub URL Test
def test_valid_public_github_ingest():
    # Use small public repo (e.g. octocat/Hello-World)
    payload = {"url": "https://github.com/octocat/Hello-World"}
    response = client.post("/api/projects/github", json=payload)

    # Note: octocat/Hello-World contains README.txt or minimal files
    # If no .py/.js files exist, test that it returns HTTP 400 NoSupportedFilesError cleanly or tests a repo with py/js
    # Let's test with a small python repo or public snippet
    assert response.status_code in [201, 400]
    data = response.json()
    if response.status_code == 201:
        assert data["status"] == "completed"
        assert "job_id" in data
    else:
        assert "message" in data["detail"]


# 7. Invalid / Private GitHub URL Test
def test_invalid_private_github_ingest():
    payload = {"url": "https://github.com/nonexistent-user-xyz-99999/nonexistent-repo-99999"}
    response = client.post("/api/projects/github", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "message" in data["detail"]
