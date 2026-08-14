"""
Refactor Validator — Runs existing generated unit tests against proposed refactored code
inside the isolated Docker container to measure non-regression equivalence and test pass rates.
"""
import os
import shutil
from typing import Optional, List, Dict
from app.analyzers.base.schema import ProjectAnalysis
from app.refactor.schema import ValidationComparison
from app.runners.schema import TestExecutionResult
from app.runners.docker_runner import DockerRunner, docker_runner


class RefactorValidator:
    """
    Validates refactored source code by executing unit tests in an isolated sandbox.
    """
    __test__ = False

    def __init__(self, runner: Optional[DockerRunner] = None):
        self._runner = runner

    @property
    def runner(self):
        if self._runner is None:
            self._runner = docker_runner
        return self._runner

    def validate_refactor(
        self,
        job_dir: str,
        project: ProjectAnalysis,
        orig_exec: Optional[TestExecutionResult] = None,
        orig_coverage: Optional[float] = None,
    ) -> ValidationComparison:
        """
        Executes test suite on refactored code in an isolated workspace.
        """
        refactored_dir = os.path.join(job_dir, "refactored")
        tests_dir = os.path.join(job_dir, "generated_tests")

        # If no tests or no refactored files exist, return skipped status
        if not os.path.exists(tests_dir) or not os.listdir(tests_dir):
            return ValidationComparison(
                status="skipped",
                error="No generated tests available to validate refactored code against.",
            )

        if not os.path.exists(refactored_dir):
            return ValidationComparison(
                status="skipped",
                error="No refactored files found to validate.",
            )

        val_workspace = os.path.join(job_dir, "validation_sandbox")
        if os.path.exists(val_workspace):
            shutil.rmtree(val_workspace, ignore_errors=True)
        os.makedirs(val_workspace, exist_ok=True)

        try:
            # 1. Copy full project to validation workspace:
            # First copy original files
            for fa in project.files:
                src = os.path.join(job_dir, fa.path)
                dest = os.path.join(val_workspace, fa.path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                if os.path.exists(src):
                    shutil.copy2(src, dest)

            # Overlay refactored files
            for root, _, files in os.walk(refactored_dir):
                for fname in files:
                    full_src = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_src, refactored_dir)
                    dest = os.path.join(val_workspace, rel_path)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(full_src, dest)

            # Copy generated tests
            dest_tests = os.path.join(val_workspace, "generated_tests")
            shutil.copytree(tests_dir, dest_tests, dirs_exist_ok=True)

            # 2. Run tests in Docker container
            primary_lang = project.languages[0] if project.languages else "python"
            framework = "pytest" if primary_lang == "python" else "vitest"

            ref_exec: TestExecutionResult = self.runner.run_tests(
                val_workspace, language=primary_lang, framework=framework
            )

            # 3. Detect regressions (tests that passed originally but failed on refactored code)
            regressions: List[str] = []
            orig_passed_names = set()
            if orig_exec and orig_exec.test_cases:
                orig_passed_names = {tc.name for tc in orig_exec.test_cases if tc.status == "passed"}

            if ref_exec.test_cases:
                for tc in ref_exec.test_cases:
                    if tc.status == "failed" and tc.name in orig_passed_names:
                        regressions.append(tc.name)
            elif ref_exec.failed_tests > 0 and orig_exec and orig_exec.passed_tests > 0:
                regressions.append(f"{ref_exec.failed_tests} test(s) failed on refactored code")

            # 4. Determine equivalence status
            if ref_exec.status == "docker_unavailable":
                status = "validation_failed"
            elif ref_exec.exit_code == 0 and len(regressions) == 0:
                status = "verified"
            elif len(regressions) > 0 or ref_exec.failed_tests > 0:
                status = "regressions_detected"
            else:
                status = "validation_failed"

            # 5. Coverage delta
            ref_cov_pct = None
            delta = None
            if ref_exec.coverage_report:
                ref_cov_pct = ref_exec.coverage_report.overall_coverage_percent
                if orig_coverage is not None:
                    delta = round(ref_cov_pct - orig_coverage, 2)

            return ValidationComparison(
                status=status,
                original_tests_passed=orig_exec.passed_tests if orig_exec else 0,
                original_tests_failed=orig_exec.failed_tests if orig_exec else 0,
                refactored_tests_passed=ref_exec.passed_tests,
                refactored_tests_failed=ref_exec.failed_tests,
                regressions=regressions,
                original_coverage_percent=orig_coverage,
                refactored_coverage_percent=ref_cov_pct,
                coverage_delta=delta,
                stdout=ref_exec.stdout,
                stderr=ref_exec.stderr,
                error=ref_exec.error,
            )

        finally:
            # Clean up temporary sandbox directory
            if os.path.exists(val_workspace):
                shutil.rmtree(val_workspace, ignore_errors=True)


# Global singleton
refactor_validator = RefactorValidator()
