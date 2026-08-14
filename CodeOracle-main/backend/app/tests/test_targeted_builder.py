"""
Phase 6 Unit Tests — Targeted context builder for uncovered functions and lines.
"""
import pytest
from app.analyzers.base.schema import (
    FileAnalysis, FunctionSymbol, ParameterSymbol, ClassSymbol
)
from app.coverage.schema import FileCoverage
from app.coverage.targeted_builder import TargetedContextBuilder


def test_targeted_builder_intersects_uncovered_function():
    fa = FileAnalysis(
        path="billing.py",
        language="python",
        total_lines=30,
        functions=[
            FunctionSymbol(name="calculate_tax", start_line=1, end_line=10,
                           parameters=[ParameterSymbol(name="amount", type_annotation="float")],
                           return_type="float"),
            FunctionSymbol(name="apply_rebate", start_line=15, end_line=25,
                           parameters=[ParameterSymbol(name="code", type_annotation="str")]),
        ],
    )

    cov = FileCoverage(
        path="billing.py",
        language="python",
        total_lines=30,
        covered_lines_count=10,
        uncovered_lines_count=20,
        coverage_percent=33.33,
        covered_lines=[1, 2, 3, 4, 5],
        uncovered_lines=[16, 17, 18, 19, 20],  # Intersects apply_rebate
    )

    builder = TargetedContextBuilder()
    context_str, uncovered_funcs = builder.build_uncovered_context(fa, cov)

    assert "apply_rebate" in uncovered_funcs
    assert "apply_rebate" in context_str
    assert "Lines 15-25" in context_str
    assert "calculate_tax" not in uncovered_funcs


def test_targeted_builder_class_methods():
    fa = FileAnalysis(
        path="engine.py",
        language="python",
        total_lines=40,
        classes=[
            ClassSymbol(
                name="TaxEngine",
                start_line=1,
                end_line=35,
                methods=[
                    FunctionSymbol(name="compute", start_line=5, end_line=15),
                    FunctionSymbol(name="exempt_check", start_line=20, end_line=30),
                ]
            )
        ]
    )

    cov = FileCoverage(
        path="engine.py",
        language="python",
        total_lines=40,
        covered_lines_count=10,
        uncovered_lines_count=10,
        coverage_percent=50.0,
        covered_lines=[5, 6, 7],
        uncovered_lines=[22, 23, 24],
    )

    builder = TargetedContextBuilder()
    context_str, uncovered_funcs = builder.build_uncovered_context(fa, cov)

    assert "TaxEngine.exempt_check" in uncovered_funcs
    assert "TaxEngine" in context_str
    assert "exempt_check" in context_str
