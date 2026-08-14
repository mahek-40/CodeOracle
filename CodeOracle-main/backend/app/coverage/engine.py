"""
Coverage improvement engine — orchestrates the iterative targeted test generation
and Docker sandbox execution loop with bounded retries to achieve >60% line coverage.
"""
import os
import ast
import time
from typing import Optional, List, Dict, Any
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.graph.schema import DependencyGraph
from app.ai.provider import GeminiProvider, AIProviderError, gemini_provider
from app.ai.coverage_prompts import (
    targeted_python_coverage_prompt,
    targeted_javascript_coverage_prompt,
)
from app.coverage.schema import (
    CoverageReport,
    FileCoverage,
    CoverageIteration,
    CoverageImprovementResult,
)
from app.coverage.targeted_builder import (
    TargetedContextBuilder,
    targeted_context_builder,
)

MAX_COVERAGE_RETRIES = 3
TARGET_COVERAGE_PERCENT = 60.0
INTER_RETRY_DELAY_SECS = 0.3


def _clean_code_blocks(text: str) -> str:
    """Strips markdown code fences (```python ... ```) and extracts raw source code."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 1 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _derive_module_name(file_path: str) -> str:
    """Converts a relative file path (e.g. src/utils.py or server.py) into an import identifier."""
    clean_path = file_path.replace("\\", "/")
    if clean_path.endswith(".py"):
        clean_path = clean_path[:-3]
    elif clean_path.endswith((".js", ".ts", ".jsx", ".tsx")):
        clean_path = clean_path.rsplit(".", 1)[0]
    return clean_path.replace("/", ".")


class CoverageEngine:
    """
    Manages real line coverage measurement and targeted test generation iterations.
    """
    __test__ = False

    def __init__(
        self,
        provider: Optional[GeminiProvider] = None,
        targeted_builder: Optional[TargetedContextBuilder] = None,
        generator: Optional[Any] = None,
        runner: Optional[Any] = None,
        max_retries: int = MAX_COVERAGE_RETRIES,
        target_coverage: float = TARGET_COVERAGE_PERCENT,
    ):
        self._provider = provider
        self._builder = targeted_builder
        self._generator = generator
        self._runner = runner
        self.max_retries = max_retries
        self.target_coverage = target_coverage

    @property
    def provider(self):
        if self._provider is None:
            self._provider = gemini_provider
        return self._provider

    @property
    def builder(self):
        if self._builder is None:
            self._builder = targeted_context_builder
        return self._builder

    @property
    def generator(self):
        if self._generator is None:
            from app.runners.test_generator import test_generator
            self._generator = test_generator
        return self._generator

    @property
    def runner(self):
        if self._runner is None:
            from app.runners.docker_runner import docker_runner
            self._runner = docker_runner
        return self._runner

    def measure_coverage(
        self,
        project: ProjectAnalysis,
        job_dir: str,
        graph: Optional[DependencyGraph] = None,
    ) -> CoverageReport:
        """
        Runs the existing generated test suite and returns the real measured coverage report.
        """
        job_id = os.path.basename(job_dir)
        primary_lang = project.languages[0] if project.languages else "python"
        framework = "pytest" if primary_lang == "python" else "vitest"

        # Check if tests exist; if not, generate initial tests
        tests_dir = os.path.join(job_dir, "generated_tests")
        if not os.path.exists(tests_dir) or not os.listdir(tests_dir):
            self.generator.generate_tests(project, job_dir, graph)

        # Run in Docker sandbox with coverage
        exec_result = self.runner.run_tests(job_dir, language=primary_lang, framework=framework)

        if exec_result.coverage_report:
            return exec_result.coverage_report

        # If execution failed or coverage was not produced, return explicit failed report
        failure_stage = exec_result.stage or "coverage_collection"
        error_msg = exec_result.error or f"Coverage report was not produced by the test runner (stage: {failure_stage})."

        return CoverageReport(
            job_id=job_id,
            language=primary_lang,
            total_lines=project.total_lines,
            total_covered_lines=0,
            total_uncovered_lines=0,
            overall_coverage_percent=0.0,
            target_reached=False,
            status="failed",
            stage=failure_stage,
            error=error_msg,
            install_logs=exec_result.install_logs,
            execution_logs=exec_result.execution_logs,
            files=[],
            timestamp=time.time(),
        )

    def improve_coverage(
        self,
        project: ProjectAnalysis,
        job_dir: str,
        graph: Optional[DependencyGraph] = None,
    ) -> CoverageImprovementResult:
        """
        Executes iterative targeted coverage improvement workflow:
        1. Measure baseline coverage.
        2. If >= 60.0%, stop immediately.
        3. Identify files contributing most to uncovered lines.
        4. Send ONLY targeted uncovered context to Gemini.
        5. Generate additional targeted test files.
        6. Re-run in Docker sandbox with coverage.
        7. Repeat up to MAX_COVERAGE_RETRIES (bounded limit).
        """
        job_id = os.path.basename(job_dir)
        primary_lang = project.languages[0] if project.languages else "python"
        framework = "pytest" if primary_lang == "python" else "vitest"

        iterations: List[CoverageIteration] = []

        # ─── Baseline Measurement (Iteration 0) ──────────────────────────────
        baseline_report = self.measure_coverage(project, job_dir, graph)
        initial_cov = baseline_report.overall_coverage_percent
        current_cov = initial_cov
        current_report = baseline_report

        iterations.append(CoverageIteration(
            iteration=0,
            test_count=baseline_report.total_covered_lines,
            coverage_percent=initial_cov,
            coverage_gain=0.0,
            new_tests_generated=0,
            target_uncovered_areas=[f.path for f in baseline_report.files if f.coverage_percent < 100.0],
            timestamp=time.time(),
        ))

        # If baseline coverage failed (e.g. dependency error or execution crash), return failure immediately
        if baseline_report.status == "failed" or not baseline_report.files:
            return CoverageImprovementResult(
                job_id=job_id,
                initial_coverage=0.0,
                final_coverage=0.0,
                coverage_gain=0.0,
                target_reached=False,
                status="failed",
                total_iterations=1,
                iterations=iterations,
                latest_report=baseline_report,
                error=baseline_report.error or f"Baseline coverage measurement failed (stage: {baseline_report.stage}).",
            )

        # Check stopping condition right away
        if current_cov >= self.target_coverage:
            return CoverageImprovementResult(
                job_id=job_id,
                initial_coverage=initial_cov,
                final_coverage=current_cov,
                coverage_gain=0.0,
                target_reached=True,
                status="target_reached",
                total_iterations=1,
                iterations=iterations,
                latest_report=current_report,
            )

        # ─── Iterative Targeted Loop (Bounded to MAX_COVERAGE_RETRIES) ───────
        tests_dir = os.path.join(job_dir, "generated_tests")
        os.makedirs(tests_dir, exist_ok=True)

        for retry_num in range(1, self.max_retries + 1):
            time.sleep(INTER_RETRY_DELAY_SECS)
            retry_start_time = time.time()

            # Find files that need additional coverage, sorted by most uncovered lines
            files_to_improve = [
                f for f in current_report.files
                if f.coverage_percent < self.target_coverage or f.uncovered_lines_count > 0
            ]
            files_to_improve.sort(key=lambda x: x.uncovered_lines_count, reverse=True)

            if not files_to_improve:
                break

            new_tests_count = 0
            targeted_areas: List[str] = []

            # Generate targeted tests for top 3 uncovered files per iteration to stay bounded
            for file_cov in files_to_improve[:3]:
                # Find matching FileAnalysis
                fa = next((f for f in project.files if f.path == file_cov.path), None)
                if not fa:
                    continue

                uncovered_ctx, uncovered_funcs = self.builder.build_uncovered_context(fa, file_cov)
                if not uncovered_funcs:
                    continue

                targeted_areas.extend([f"{fa.path}:{fn}" for fn in uncovered_funcs[:3]])

                if fa.language == "python":
                    mod_name = _derive_module_name(fa.path)
                    prompt = targeted_python_coverage_prompt(fa.path, mod_name, uncovered_ctx)
                    stem = os.path.basename(fa.path).rsplit(".", 1)[0]
                    test_file_name = f"test_targeted_{stem}_iter{retry_num}.py"
                else:
                    import_path = f"../{fa.path}".replace("\\", "/")
                    prompt = targeted_javascript_coverage_prompt(fa.path, import_path, uncovered_ctx, framework)
                    stem = os.path.basename(fa.path).rsplit(".", 1)[0]
                    test_file_name = f"{stem}.targeted.iter{retry_num}.test.js"

                try:
                    raw_code = self.provider.generate(prompt, temperature=0.1)
                    clean_code = _clean_code_blocks(raw_code)

                    if fa.language == "python":
                        try:
                            ast.parse(clean_code)
                        except SyntaxError:
                            pass

                    # Write new targeted test file to disk
                    dest_path = os.path.join(tests_dir, test_file_name)
                    with open(dest_path, "w", encoding="utf-8") as f:
                        f.write(clean_code)

                    new_tests_count += 1
                except AIProviderError:
                    # Continue to other files if single call fails
                    continue

            # Execute updated suite with Docker runner
            exec_res = self.runner.run_tests(job_dir, language=primary_lang, framework=framework)
            duration_ms = int((time.time() - retry_start_time) * 1000)

            if exec_res.coverage_report:
                current_report = exec_res.coverage_report
                prev_cov = current_cov
                current_cov = current_report.overall_coverage_percent
                gain = round(current_cov - prev_cov, 2)
            else:
                gain = 0.0

            iterations.append(CoverageIteration(
                iteration=retry_num,
                test_count=exec_res.total_tests,
                coverage_percent=current_cov,
                coverage_gain=gain,
                new_tests_generated=new_tests_count,
                target_uncovered_areas=targeted_areas,
                duration_ms=duration_ms,
                timestamp=time.time(),
            ))

            # Check if target is achieved
            if current_cov >= self.target_coverage:
                return CoverageImprovementResult(
                    job_id=job_id,
                    initial_coverage=initial_cov,
                    final_coverage=current_cov,
                    coverage_gain=round(current_cov - initial_cov, 2),
                    target_reached=True,
                    status="target_reached",
                    total_iterations=len(iterations),
                    iterations=iterations,
                    latest_report=current_report,
                )

        # Loop completed without reaching 60%
        final_gain = round(current_cov - initial_cov, 2)
        return CoverageImprovementResult(
            job_id=job_id,
            initial_coverage=initial_cov,
            final_coverage=current_cov,
            coverage_gain=final_gain,
            target_reached=(current_cov >= self.target_coverage),
            status="max_retries_reached" if current_cov < self.target_coverage else "target_reached",
            total_iterations=len(iterations),
            iterations=iterations,
            latest_report=current_report,
        )


# Global singleton
coverage_engine = CoverageEngine()
