"""
Phase 6 Unit Tests — Iterative coverage engine, bounded retry logic, stopping conditions.
"""
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from app.analyzers.base.schema import (
    ProjectAnalysis, FileAnalysis, FunctionSymbol, ParameterSymbol
)
from app.coverage.schema import (
    CoverageReport, FileCoverage, CoverageImprovementResult
)
from app.coverage.engine import CoverageEngine
from app.runners.schema import TestExecutionResult
from app.ai.provider import GeminiProvider


def _make_sample_project(total_lines: int = 20) -> ProjectAnalysis:
    fa = FileAnalysis(
        path="math_ops.py",
        language="python",
        total_lines=total_lines,
        functions=[
            FunctionSymbol(name="add", start_line=1, end_line=5),
            FunctionSymbol(name="multiply", start_line=6, end_line=15),
        ],
    )
    return ProjectAnalysis(
        root_dir="/tmp/test",
        total_files=1,
        total_lines=total_lines,
        languages=["python"],
        files=[fa],
    )


def test_coverage_engine_baseline_already_above_target():
    """If initial baseline coverage is >= 60%, engine stops immediately without calling AI."""
    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = TestExecutionResult(
        job_id="job-1",
        status="passed",
        framework="pytest",
        coverage_report=CoverageReport(
            job_id="job-1",
            language="python",
            total_lines=20,
            total_covered_lines=15,
            total_uncovered_lines=5,
            overall_coverage_percent=75.0,
            target_reached=True,
            files=[
                FileCoverage(
                    path="math_ops.py",
                    language="python",
                    total_lines=20,
                    covered_lines_count=15,
                    uncovered_lines_count=5,
                    coverage_percent=75.0,
                )
            ]
        )
    )

    mock_provider = MagicMock(spec=GeminiProvider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = CoverageEngine(provider=mock_provider, runner=mock_runner, max_retries=3)
        pa = _make_sample_project()
        result = engine.improve_coverage(pa, tmp_dir)

        assert isinstance(result, CoverageImprovementResult)
        assert result.status == "target_reached"
        assert result.target_reached is True
        assert result.final_coverage == 75.0
        assert result.total_iterations == 1
        assert mock_provider.generate.call_count == 0  # No AI calls needed


def test_coverage_engine_improves_coverage_to_target():
    """Engine generates targeted tests on retry 1 and reaches >=60% coverage."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.generate.return_value = "def test_multiply(): assert multiply(2, 3) == 6"

    # Sequence of test execution results:
    # Run 0 (Baseline): 40% coverage
    # Run 1 (After targeted test): 70% coverage
    baseline_cov = CoverageReport(
        job_id="job-2",
        language="python",
        total_lines=20,
        total_covered_lines=8,
        total_uncovered_lines=12,
        overall_coverage_percent=40.0,
        target_reached=False,
        files=[
            FileCoverage(
                path="math_ops.py",
                language="python",
                total_lines=20,
                covered_lines_count=8,
                uncovered_lines_count=12,
                coverage_percent=40.0,
                uncovered_lines=[6, 7, 8, 9, 10],
            )
        ]
    )

    improved_cov = CoverageReport(
        job_id="job-2",
        language="python",
        total_lines=20,
        total_covered_lines=14,
        total_uncovered_lines=6,
        overall_coverage_percent=70.0,
        target_reached=True,
        files=[
            FileCoverage(
                path="math_ops.py",
                language="python",
                total_lines=20,
                covered_lines_count=14,
                uncovered_lines_count=6,
                coverage_percent=70.0,
                uncovered_lines=[],
            )
        ]
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.side_effect = [
        TestExecutionResult(job_id="job-2", status="passed", framework="pytest", coverage_report=baseline_cov),
        TestExecutionResult(job_id="job-2", status="passed", framework="pytest", coverage_report=improved_cov),
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = CoverageEngine(provider=mock_provider, runner=mock_runner, max_retries=3)
        pa = _make_sample_project()
        result = engine.improve_coverage(pa, tmp_dir)

        assert result.target_reached is True
        assert result.status == "target_reached"
        assert result.initial_coverage == 40.0
        assert result.final_coverage == 70.0
        assert result.coverage_gain == 30.0
        assert len(result.iterations) == 2
        assert mock_provider.generate.call_count == 1


def test_coverage_engine_stops_at_max_retries():
    """Engine stops cleanly when max retries limit is reached."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.generate.return_value = "def test_more(): pass"

    low_cov = CoverageReport(
        job_id="job-3",
        language="python",
        total_lines=20,
        total_covered_lines=6,
        total_uncovered_lines=14,
        overall_coverage_percent=30.0,
        target_reached=False,
        files=[
            FileCoverage(
                path="math_ops.py",
                language="python",
                total_lines=20,
                covered_lines_count=6,
                uncovered_lines_count=14,
                coverage_percent=30.0,
                uncovered_lines=[6, 7, 8],
            )
        ]
    )

    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = TestExecutionResult(
        job_id="job-3", status="passed", framework="pytest", coverage_report=low_cov
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Max retries = 2
        engine = CoverageEngine(provider=mock_provider, runner=mock_runner, max_retries=2)
        pa = _make_sample_project()
        result = engine.improve_coverage(pa, tmp_dir)

        assert result.status == "max_retries_reached"
        assert result.target_reached is False
        # Baseline + 2 retries = 3 iterations
        assert len(result.iterations) == 3
        assert mock_provider.generate.call_count == 2
