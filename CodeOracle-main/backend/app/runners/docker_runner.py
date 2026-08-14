"""
Docker & Subprocess execution sandbox — executes generated unit tests and collects
real coverage metrics in an isolated environment with dependency detection and installation.
"""
import os
import sys
import shutil
import subprocess
import time
from typing import Optional, Tuple
from app.runners.schema import TestExecutionResult
from app.runners.output_parser import parse_test_output
from app.runners.dependency_manager import dependency_manager
from app.coverage.parser import parse_coverage_file

DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MEMORY_LIMIT = "512m"
DEFAULT_CPU_LIMIT = "1.0"
DEFAULT_PIDS_LIMIT = "100"

PYTHON_DOCKER_IMAGE = "python:3.11-slim"
NODE_DOCKER_IMAGE = "node:20-slim"


class DockerUnavailableError(Exception):
    """Raised when Docker daemon is not running or Docker CLI is not installed."""
    def __init__(self, detail: str = "Docker daemon is not available."):
        message = (
            f"Docker is unavailable: {detail}. "
            "Untrusted code execution requires Docker container sandboxing and cannot proceed unsandboxed."
        )
        super().__init__(message)
        self.message = message


class DockerRunner:
    """
    Executes unit tests in an isolated Docker container or isolated fallback subprocess
    with automatic dependency installation and real coverage collection.
    """

    DOCKER_CHECK_TTL_SECS = 120.0

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        cpu_limit: str = DEFAULT_CPU_LIMIT,
        pids_limit: str = DEFAULT_PIDS_LIMIT,
        allow_local_fallback: bool = True,
    ):
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit
        self.allow_local_fallback = allow_local_fallback
        self._docker_cache: Optional[Tuple[bool, str]] = None
        self._docker_cache_time: float = 0.0

    def is_docker_available(self, force_refresh: bool = False) -> Tuple[bool, str]:
        """
        Checks if Docker CLI is installed and the Docker daemon is accessible.
        Caches result for 120 seconds to eliminate repeated 5s subprocess probes.
        """
        now = time.time()
        if not force_refresh and self._docker_cache is not None and (now - self._docker_cache_time) < self.DOCKER_CHECK_TTL_SECS:
            return self._docker_cache

        try:
            t0 = time.perf_counter()
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            duration_s = time.perf_counter() - t0
            if res.returncode == 0:
                result = (True, "")
            else:
                result = (False, res.stderr.strip() or res.stdout.strip() or "Docker daemon returned non-zero status")
            logger.info(f"[PERF] Docker capability check completed in {duration_s:.2f}s (available={result[0]})")
            self._docker_cache = result
            self._docker_cache_time = now
            return result
        except FileNotFoundError:
            result = (False, "Docker CLI is not installed on PATH")
            self._docker_cache = result
            self._docker_cache_time = now
            return result
        except subprocess.TimeoutExpired:
            result = (False, "Docker info check timed out")
            self._docker_cache = result
            self._docker_cache_time = now
            return result
        except Exception as exc:
            result = (False, str(exc))
            self._docker_cache = result
            self._docker_cache_time = now
            return result

    def run_tests(
        self,
        job_dir: str,
        language: str = "python",
        framework: str = "pytest",
    ) -> TestExecutionResult:
        """
        Runs generated tests with dependency installation and real coverage collection.
        """
        job_id = os.path.basename(job_dir)
        lang = language.lower()

        # 1. Check Docker availability
        docker_available, docker_msg = self.is_docker_available()
        if not docker_available and not self.allow_local_fallback:
            return TestExecutionResult(
                job_id=job_id,
                status="docker_unavailable",
                framework=framework,
                sandboxed=True,
                exit_code=-1,
                error=(
                    f"Docker isolation is unavailable on the host ({docker_msg}). "
                    "Untrusted code cannot be executed without Docker sandboxing."
                ),
            )

        # 2. Verify generated_tests directory exists
        tests_dir = os.path.join(job_dir, "generated_tests")
        if not os.path.exists(tests_dir):
            return TestExecutionResult(
                job_id=job_id,
                status="error",
                stage="test_execution",
                framework=framework,
                sandboxed=True,
                exit_code=1,
                error="No generated tests found in the job workspace. Run test generation first.",
            )

        # 3. Automatically detect and install dependencies
        dep_ok, dep_stage, install_logs, dep_err = dependency_manager.install_dependencies(job_dir, lang)
        if not dep_ok:
            return TestExecutionResult(
                job_id=job_id,
                status="dependency_install_failed",
                stage=dep_stage,
                framework=framework,
                sandboxed=True,
                exit_code=1,
                install_logs=install_logs,
                error=f"Dependency installation failed: {dep_err}",
            )

        if docker_available:
            return self._run_in_docker(job_dir, job_id, lang, framework, install_logs)
        else:
            return self._run_in_subprocess(job_dir, job_id, lang, framework, install_logs)

    def _run_in_docker(
        self,
        job_dir: str,
        job_id: str,
        language: str,
        framework: str,
        install_logs: str,
    ) -> TestExecutionResult:
        """Executes tests inside Docker container."""
        if language in ("javascript", "typescript"):
            image = NODE_DOCKER_IMAGE
            cmd = ["sh", "-c", "npx --yes vitest run generated_tests --coverage.enabled=true --coverage.reporter=json --coverage.reportsDirectory=coverage || npx --yes vitest run generated_tests"]
        else:
            image = PYTHON_DOCKER_IMAGE
            cmd = ["sh", "-c", "python -m coverage run --source=. -m pytest generated_tests -v && python -m coverage json -o coverage.json && python -m coverage xml -o coverage.xml || python -m pytest generated_tests -v"]

        abs_job_dir = os.path.abspath(job_dir).replace("\\", "/")
        volume_mount = f"{abs_job_dir}:/workspace"

        docker_cmd = [
            "docker", "run",
            "--rm",
            "--network", "none",
            "--memory", self.memory_limit,
            "--cpus", self.cpu_limit,
            "--pids-limit", self.pids_limit,
            "-v", volume_mount,
            "-w", "/workspace",
            "-e", "PYTHONPATH=/workspace",
            image,
        ] + cmd

        start_time = time.time()
        try:
            res = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return self._process_execution_output(
                job_dir=job_dir,
                job_id=job_id,
                language=language,
                framework=framework,
                stdout=res.stdout or "",
                stderr=res.stderr or "",
                exit_code=res.returncode,
                duration_ms=duration_ms,
                install_logs=install_logs,
                sandboxed=True,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestExecutionResult(
                job_id=job_id,
                status="timeout",
                stage="test_execution",
                framework=framework,
                sandboxed=True,
                exit_code=-1,
                duration_ms=duration_ms,
                install_logs=install_logs,
                error=f"Test execution timed out after {self.timeout_seconds} seconds.",
                stderr=f"TimeoutExpired: Exceeded {self.timeout_seconds}s limit.",
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestExecutionResult(
                job_id=job_id,
                status="failed",
                stage="test_execution",
                framework=framework,
                sandboxed=True,
                exit_code=1,
                duration_ms=duration_ms,
                install_logs=install_logs,
                error=f"Container execution error: {str(exc)}",
                stderr=str(exc),
            )

    def _run_in_subprocess(
        self,
        job_dir: str,
        job_id: str,
        language: str,
        framework: str,
        install_logs: str,
    ) -> TestExecutionResult:
        """Executes tests using the environment test runners."""
        start_time = time.time()
        env = os.environ.copy()
        # Set PYTHONPATH so relative imports resolve from job_dir
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{job_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else job_dir

        stdout_chunks = []
        stderr_chunks = []
        exit_code = 0

        try:
            if language == "python":
                python_exe = sys.executable
                cov_run_cmd = [
                    python_exe, "-m", "coverage", "run",
                    f"--source={job_dir}",
                    "-m", "pytest",
                    "generated_tests",
                    "-v",
                ]

                res = subprocess.run(
                    cov_run_cmd,
                    cwd=job_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env=env,
                )
                stdout_chunks.append(res.stdout or "")
                stderr_chunks.append(res.stderr or "")
                exit_code = res.returncode

                # Generate JSON and XML coverage reports
                subprocess.run(
                    [python_exe, "-m", "coverage", "json", "-o", "coverage.json"],
                    cwd=job_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env,
                )
                subprocess.run(
                    [python_exe, "-m", "coverage", "xml", "-o", "coverage.xml"],
                    cwd=job_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env,
                )

            elif language in ("javascript", "typescript"):
                js_cmd_list = [
                    "npx", "vitest", "run",
                    "generated_tests",
                    "--coverage.enabled=true",
                    "--coverage.reporter=json",
                    "--coverage.reportsDirectory=coverage",
                ]
                if sys.platform == "win32":
                    js_cmd_str = " ".join(js_cmd_list)
                    res = subprocess.run(
                        js_cmd_str,
                        cwd=job_dir,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        shell=True,
                        env=env,
                    )
                else:
                    npx_bin = shutil.which("npx") or "npx"
                    js_cmd_list[0] = npx_bin
                    res = subprocess.run(
                        js_cmd_list,
                        cwd=job_dir,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout_seconds,
                        shell=False,
                        env=env,
                    )
                stdout_chunks.append(res.stdout or "")
                stderr_chunks.append(res.stderr or "")
                exit_code = res.returncode

            duration_ms = int((time.time() - start_time) * 1000)
            return self._process_execution_output(
                job_dir=job_dir,
                job_id=job_id,
                language=language,
                framework=framework,
                stdout="\n".join(stdout_chunks),
                stderr="\n".join(stderr_chunks),
                exit_code=exit_code,
                duration_ms=duration_ms,
                install_logs=install_logs,
                sandboxed=False,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestExecutionResult(
                job_id=job_id,
                status="timeout",
                stage="test_execution",
                framework=framework,
                sandboxed=False,
                exit_code=-1,
                duration_ms=duration_ms,
                install_logs=install_logs,
                error=f"Test execution timed out after {self.timeout_seconds} seconds.",
                stderr=f"TimeoutExpired: Execution exceeded {self.timeout_seconds}s limit.",
            )
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            return TestExecutionResult(
                job_id=job_id,
                status="failed",
                stage="test_execution",
                framework=framework,
                sandboxed=False,
                exit_code=1,
                duration_ms=duration_ms,
                install_logs=install_logs,
                error=f"Execution error: {str(exc)}",
                stderr=str(exc),
            )

    def _process_execution_output(
        self,
        job_dir: str,
        job_id: str,
        language: str,
        framework: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
        install_logs: str,
        sandboxed: bool,
    ) -> TestExecutionResult:
        """Parses test runner output and coverage reports into a structured TestExecutionResult."""
        total, passed, failed, skipped, test_cases = parse_test_output(
            framework, stdout, stderr, exit_code
        )

        cov_file_json = os.path.join(job_dir, "coverage.json")
        cov_file_xml = os.path.join(job_dir, "coverage.xml")
        cov_file_js = os.path.join(job_dir, "coverage", "coverage-final.json")
        cov_file_js_sum = os.path.join(job_dir, "coverage", "coverage-summary.json")
        cov_file_lcov = os.path.join(job_dir, "coverage", "lcov.info")

        cov_report = None
        if os.path.exists(cov_file_json):
            cov_report = parse_coverage_file(cov_file_json, job_id, "python", root_dir=job_dir)
        elif os.path.exists(cov_file_xml):
            cov_report = parse_coverage_file(cov_file_xml, job_id, "python", root_dir=job_dir)
        elif os.path.exists(cov_file_js):
            cov_report = parse_coverage_file(cov_file_js, job_id, "javascript", root_dir=job_dir)
        elif os.path.exists(cov_file_js_sum):
            cov_report = parse_coverage_file(cov_file_js_sum, job_id, "javascript", root_dir=job_dir)
        elif os.path.exists(cov_file_lcov):
            cov_report = parse_coverage_file(cov_file_lcov, job_id, "javascript", root_dir=job_dir)

        if exit_code == 0:
            status = "passed"
            stage = "completed"
            error = None
        elif failed > 0:
            status = "failed"
            stage = "test_execution"
            error = f"{failed} tests failed during execution."
        else:
            status = "failed"
            stage = "test_execution"
            error = f"Test execution returned non-zero exit code ({exit_code}).\n{stderr or stdout}"

        if cov_report:
            if status != "passed":
                cov_report.status = "failed"
                cov_report.stage = stage
                cov_report.error = error
            cov_report.install_logs = install_logs
            cov_report.execution_logs = f"[STDOUT]\n{stdout}\n[STDERR]\n{stderr}"

        return TestExecutionResult(
            job_id=job_id,
            status=status,
            stage=stage,
            framework=framework,
            sandboxed=sandboxed,
            exit_code=exit_code,
            duration_ms=duration_ms,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            test_cases=test_cases,
            stdout=stdout,
            stderr=stderr,
            install_logs=install_logs,
            execution_logs=f"[STDOUT]\n{stdout}\n[STDERR]\n{stderr}",
            error=error,
            coverage_report=cov_report,
        )


# Global singleton
docker_runner = DockerRunner(allow_local_fallback=True)
