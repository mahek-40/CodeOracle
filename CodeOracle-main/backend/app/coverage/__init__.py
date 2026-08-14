"""
Coverage package — real test coverage measurement and targeted improvement.
"""
from app.coverage.schema import (
    FileCoverage,
    CoverageReport,
    CoverageIteration,
    CoverageImprovementResult,
)
from app.coverage.parser import (
    parse_python_coverage_json,
    parse_javascript_coverage_json,
    parse_coverage_file,
)
from app.coverage.targeted_builder import (
    TargetedContextBuilder,
    targeted_context_builder,
)
from app.coverage.engine import (
    CoverageEngine,
    coverage_engine,
)

__all__ = [
    "FileCoverage",
    "CoverageReport",
    "CoverageIteration",
    "CoverageImprovementResult",
    "parse_python_coverage_json",
    "parse_javascript_coverage_json",
    "parse_coverage_file",
    "TargetedContextBuilder",
    "targeted_context_builder",
    "CoverageEngine",
    "coverage_engine",
]
