from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.coverage.schema import CoverageReport


class GeneratedTestFile(BaseModel):
    """Represents an AI-generated test file stored on disk."""
    path: str
    filename: str
    target_file: str
    language: str
    content: str
    num_tests_estimated: int = 0
    error: Optional[str] = None


class TestGenerationResult(BaseModel):
    """Result of generating test suites for an analysed project."""
    __test__ = False
    job_id: str
    status: str  # "completed", "partial", "failed"
    framework: str  # "pytest", "vitest", etc.
    total_files: int
    generated_files: List[GeneratedTestFile] = Field(default_factory=list)
    error: Optional[str] = None


class TestCaseResult(BaseModel):
    """Individual test case execution result."""
    __test__ = False
    name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration_seconds: Optional[float] = None
    message: Optional[str] = None


class TestExecutionResult(BaseModel):
    """Output of running tests in the isolated Docker container or local test runner."""
    __test__ = False
    job_id: str
    status: str  # "passed", "failed", "error", "timeout", "docker_unavailable", "dependency_install_failed"
    stage: str = "completed"  # "dependency_installation", "test_execution", "coverage_collection", "completed", "failed"
    framework: str
    sandboxed: bool = True
    exit_code: int = 0
    duration_ms: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    test_cases: List[TestCaseResult] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    install_logs: str = ""
    execution_logs: str = ""
    error: Optional[str] = None
    coverage_report: Optional[CoverageReport] = None
    coverage_placeholder: str = "Real line coverage measured via coverage.py / Vitest."


class JobTestsData(BaseModel):
    """Combined test status for a job."""
    job_id: str
    generation: Optional[TestGenerationResult] = None
    execution: Optional[TestExecutionResult] = None
