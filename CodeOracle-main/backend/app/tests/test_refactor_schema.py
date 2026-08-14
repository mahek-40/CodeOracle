"""
Phase 7 Unit Tests — Refactoring Schema validation and models.
"""
import pytest
from app.refactor.schema import (
    DiffLine,
    FileDiff,
    ModernizationOpportunity,
    BreakingChangeWarning,
    RefactoredFile,
    RiskSummary,
    ValidationComparison,
    RefactorResult,
)


def test_refactor_schema_models():
    diff_line = DiffLine(orig_line_num=1, refactored_line_num=1, type="same", content="import os")
    assert diff_line.type == "same"

    file_diff = FileDiff(
        path="calc.py",
        additions=5,
        deletions=2,
        modifications=3,
        diff_text="--- a/calc.py\n+++ b/calc.py\n",
        diff_lines=[diff_line],
    )
    assert file_diff.additions == 5

    warning = BreakingChangeWarning(
        severity="critical",
        category="api",
        file="calc.py",
        symbol="compute",
        explanation="Public function removed",
        suggested_mitigation="Restore function",
        affected_dependents=["main.py"],
    )
    assert warning.severity == "critical"
    assert len(warning.affected_dependents) == 1

    risk = RiskSummary(
        overall_risk="high",
        critical_warnings_count=0,
        high_warnings_count=2,
        medium_warnings_count=1,
        low_warnings_count=0,
        safety_score=65,
        recommendation="Review high impact changes",
    )
    assert risk.safety_score == 65

    val = ValidationComparison(
        status="verified",
        original_tests_passed=10,
        original_tests_failed=0,
        refactored_tests_passed=10,
        refactored_tests_failed=0,
        regressions=[],
        original_coverage_percent=75.0,
        refactored_coverage_percent=80.0,
        coverage_delta=5.0,
    )
    assert val.status == "verified"
    assert val.coverage_delta == 5.0

    result = RefactorResult(
        job_id="job-123",
        status="completed",
        total_files=1,
        files_modified=1,
        total_additions=5,
        total_deletions=2,
        risk_summary=risk,
        files=[],
        all_warnings=[warning],
        all_opportunities=[],
        validation=val,
    )
    assert result.job_id == "job-123"
    assert len(result.all_warnings) == 1
