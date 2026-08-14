"""
Phase 5 Unit Tests — Docker runner sandbox, security flags, timeout enforcement, output parsing.
All Docker subprocess calls are tested with mocks where needed.
"""
import os
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from app.runners.output_parser import parse_pytest_output, parse_vitest_output, parse_test_output
from app.runners.docker_runner import DockerRunner
from app.runners.schema import TestExecutionResult


# ─── Output Parser Tests ──────────────────────────────────────────────────────

def test_parse_pytest_output_all_passed():
    stdout = """
============================= test session starts ==============================
collected 3 items

generated_tests/test_calc.py::test_add_positive PASSED                   [ 33%]
generated_tests/test_calc.py::test_add_zero PASSED                       [ 66%]
generated_tests/test_calc.py::test_add_negative PASSED                   [100%]

============================== 3 passed in 0.05s ===============================
"""
    total, passed, failed, skipped, cases = parse_pytest_output(stdout, "", 0)
    assert total == 3
    assert passed == 3
    assert failed == 0
    assert skipped == 0
    assert len(cases) == 3
    assert cases[0].status == "passed"


def test_parse_pytest_output_with_failures():
    stdout = """
============================= test session starts ==============================
generated_tests/test_calc.py::test_one PASSED                            [ 33%]
generated_tests/test_calc.py::test_two FAILED                            [ 66%]
generated_tests/test_calc.py::test_three SKIPPED                         [100%]

=================== 1 failed, 1 passed, 1 skipped in 0.12s ====================
"""
    total, passed, failed, skipped, cases = parse_pytest_output(stdout, "", 1)
    assert total == 3
    assert passed == 1
    assert failed == 1
    assert skipped == 1
    assert len(cases) == 3
    assert cases[1].status == "failed"


def test_parse_vitest_output():
    stdout = """
 ✓ src/math.test.js > adds numbers
 ✕ src/math.test.js > fails on invalid

 Test Files  1 failed (1)
      Tests  1 failed | 2 passed (3)
   Duration  412ms
"""
    total, passed, failed, skipped, cases = parse_vitest_output(stdout, "", 1)
    assert total == 3
    assert passed == 2
    assert failed == 1
    assert skipped == 0


# ─── DockerRunner Unit Tests ─────────────────────────────────────────────────

def test_docker_runner_unavailable():
    """Verify runner fails safely when Docker is not accessible."""
    runner = DockerRunner()
    with patch.object(runner, "is_docker_available", return_value=(False, "Docker daemon not running")):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = runner.run_tests(tmp_dir, language="python")
            assert isinstance(result, TestExecutionResult)
            assert result.status == "docker_unavailable"
            assert result.sandboxed is True
            assert "Docker isolation is unavailable" in result.error


def test_docker_runner_missing_tests_dir():
    """Verify error when no generated tests exist."""
    runner = DockerRunner()
    with patch.object(runner, "is_docker_available", return_value=(True, "")):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = runner.run_tests(tmp_dir, language="python")
            assert result.status == "error"
            assert "No generated tests found" in result.error


def test_docker_runner_command_security_flags():
    """Verify security constraints (--network none, resource limits) are present in docker invocation."""
    runner = DockerRunner(memory_limit="256m", cpu_limit="0.5", timeout_seconds=15)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, "generated_tests"))

        with patch.object(runner, "is_docker_available", return_value=(True, "")):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=["docker"],
                    returncode=0,
                    stdout="=== 2 passed in 0.02s ===",
                    stderr="",
                )
                result = runner.run_tests(tmp_dir, language="python")

                assert result.status == "passed"
                assert result.passed_tests == 2
                assert result.sandboxed is True

                # Inspect docker command arguments passed to subprocess.run
                called_cmd = mock_run.call_args[0][0]
                assert "--network" in called_cmd
                net_idx = called_cmd.index("--network")
                assert called_cmd[net_idx + 1] == "none"

                assert "--memory" in called_cmd
                mem_idx = called_cmd.index("--memory")
                assert called_cmd[mem_idx + 1] == "256m"

                assert "--cpus" in called_cmd
                cpu_idx = called_cmd.index("--cpus")
                assert called_cmd[cpu_idx + 1] == "0.5"

                assert "--rm" in called_cmd


def test_docker_runner_handles_timeout():
    """Verify timeout enforcement when container exceeds timeout limit."""
    runner = DockerRunner(timeout_seconds=5)

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, "generated_tests"))

        with patch.object(runner, "is_docker_available", return_value=(True, "")):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=5)):
                result = runner.run_tests(tmp_dir, language="python")
                assert result.status == "timeout"
                assert "timed out after 5 seconds" in result.error
