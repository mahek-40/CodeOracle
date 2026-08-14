"""
Unit & integration tests for DependencyManager:
- Manifest detection for Python and JavaScript
- Lockfile handling (package-lock.json -> npm ci, package.json -> npm install)
- Lockfile fallback recovery (npm ci failure -> npm install)
- No manifests found -> clean skip
- Non-existent directory handling
- Command logging and subprocess argument integrity
"""
import os
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from app.runners.dependency_manager import DependencyManager


def test_no_manifests_skips_installation():
    """Verify that workspaces without manifest files skip install cleanly."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        ok, stage, logs, err = manager.install_dependencies(tmp_dir, "python")
        assert ok is True
        assert stage == "dependency_installation"
        assert "No dependency manifests" in logs
        assert err is None


def test_non_existent_directory():
    """Verify non-existent directory returns clean failure."""
    manager = DependencyManager()
    ok, stage, logs, err = manager.install_dependencies("/non/existent/path", "python")
    assert ok is False
    assert "does not exist" in err


def test_detect_python_manifests():
    """Verify detection of requirements.txt, pyproject.toml, and setup.py."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        req_file = os.path.join(tmp_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("pytest>=8.0.0\n")

        manifests = manager.detect_dependencies(tmp_dir, "python")
        assert len(manifests) == 1
        assert manifests[0]["type"] == "requirements.txt"
        assert manifests[0]["path"] == req_file


def test_detect_js_package_json_only():
    """Verify package.json without lockfile triggers npm install."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_file = os.path.join(tmp_dir, "package.json")
        with open(pkg_file, "w") as f:
            f.write('{"name": "test-pkg", "dependencies": {}}\n')

        manifests = manager.detect_dependencies(tmp_dir, "javascript")
        assert len(manifests) == 1
        assert manifests[0]["type"] == "package.json"
        assert manifests[0]["has_lock"] is False


def test_detect_js_package_lock_triggers_npm_ci():
    """Verify package.json with package-lock.json triggers npm ci."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_file = os.path.join(tmp_dir, "package.json")
        with open(pkg_file, "w") as f:
            f.write('{"name": "test-pkg", "dependencies": {}}\n')

        lock_file = os.path.join(tmp_dir, "package-lock.json")
        with open(lock_file, "w") as f:
            f.write('{"name": "test-pkg", "lockfileVersion": 3}\n')

        manifests = manager.detect_dependencies(tmp_dir, "javascript")
        assert len(manifests) == 1
        assert manifests[0]["has_lock"] is True


def test_js_install_executes_npm_ci_and_logs():
    """Verify subprocess receives 'npm ci' command with lockfile."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_file = os.path.join(tmp_dir, "package.json")
        with open(pkg_file, "w") as f:
            f.write('{"name": "test-pkg"}\n')

        lock_file = os.path.join(tmp_dir, "package-lock.json")
        with open(lock_file, "w") as f:
            f.write('{"name": "test-pkg"}\n')

        with patch.object(manager, "_execute_command", return_value=(0, "added 5 packages in 1s", "")) as mock_exec:
            ok, stage, logs, err = manager.install_dependencies(tmp_dir, "javascript")
            assert ok is True
            assert err is None
            assert "npm ci" in logs
            assert mock_exec.called
            executed_cmd = mock_exec.call_args[0][0]
            # Command must contain 'ci' not bare 'npm'
            if isinstance(executed_cmd, list):
                assert "ci" in executed_cmd
            else:
                assert "npm ci" in executed_cmd


def test_js_install_fallback_to_npm_install_on_ci_failure():
    """Verify that if npm ci fails, it automatically retries with npm install."""
    manager = DependencyManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_file = os.path.join(tmp_dir, "package.json")
        with open(pkg_file, "w") as f:
            f.write('{"name": "test-pkg"}\n')

        lock_file = os.path.join(tmp_dir, "package-lock.json")
        with open(lock_file, "w") as f:
            f.write('{"name": "test-pkg"}\n')

        calls = []
        def mock_execute(cmd, cwd, timeout):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            calls.append(cmd_str)
            if "ci" in cmd_str:
                # npm ci fails with lockfile error
                return 1, "", "npm error code EUSAGE\nnpm error `npm ci` can only install when package-lock.json is in sync."
            else:
                # fallback npm install succeeds
                return 0, "added 12 packages in 2s", ""

        with patch.object(manager, "_execute_command", side_effect=mock_execute):
            ok, stage, logs, err = manager.install_dependencies(tmp_dir, "javascript")
            assert ok is True
            assert err is None
            assert len(calls) == 2
            assert "ci" in calls[0]
            assert "install" in calls[1]
            assert "[FALLBACK]" in logs
