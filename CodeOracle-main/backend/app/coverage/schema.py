from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FileCoverage(BaseModel):
    """Line coverage breakdown for an individual source file."""
    __test__ = False
    path: str
    language: str
    total_lines: int
    covered_lines_count: int
    uncovered_lines_count: int
    coverage_percent: float
    covered_lines: List[int] = Field(default_factory=list)
    uncovered_lines: List[int] = Field(default_factory=list)
    uncovered_functions: List[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    """Normalized project-wide coverage metrics."""
    __test__ = False
    job_id: str
    language: str
    total_lines: int
    total_covered_lines: int
    total_uncovered_lines: int
    overall_coverage_percent: float
    target_reached: bool = False  # True if >= 60.0%
    status: str = "completed"  # "completed", "failed", "coverage_unavailable", "dependency_install_failed"
    stage: Optional[str] = None  # "dependency_installation", "test_execution", "coverage_collection", "completed"
    error: Optional[str] = None
    install_logs: Optional[str] = None
    execution_logs: Optional[str] = None
    files: List[FileCoverage] = Field(default_factory=list)
    timestamp: float = 0.0


class CoverageIteration(BaseModel):
    """Record of a single retry step in the targeted improvement loop."""
    __test__ = False
    iteration: int
    test_count: int
    coverage_percent: float
    coverage_gain: float
    new_tests_generated: int
    target_uncovered_areas: List[str] = Field(default_factory=list)
    duration_ms: int = 0
    timestamp: float = 0.0


class CoverageImprovementResult(BaseModel):
    """Summary of the iterative coverage improvement workflow."""
    __test__ = False
    job_id: str
    initial_coverage: float
    final_coverage: float
    coverage_gain: float
    target_reached: bool
    status: str  # "completed", "target_reached", "max_retries_reached", "failed"
    total_iterations: int
    iterations: List[CoverageIteration] = Field(default_factory=list)
    latest_report: Optional[CoverageReport] = None
    error: Optional[str] = None
