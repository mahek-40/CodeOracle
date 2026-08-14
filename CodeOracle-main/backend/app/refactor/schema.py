"""
Refactoring Schema — Normalized data models for proposed refactored code,
structured diffs, modernization opportunities, breaking-change warnings, and test validation comparisons.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DiffLine(BaseModel):
    """Represents a single line in a side-by-side or unified diff."""
    orig_line_num: Optional[int] = None
    refactored_line_num: Optional[int] = None
    type: str  # "same", "add", "del", "mod"
    content: str


class FileDiff(BaseModel):
    """Structured line-by-line and summary diff for a single file."""
    path: str
    additions: int = 0
    deletions: int = 0
    modifications: int = 0
    diff_text: str = ""
    diff_lines: List[DiffLine] = Field(default_factory=list)


class ModernizationOpportunity(BaseModel):
    """Specific modernization pattern detected and applied."""
    category: str  # "syntax", "types", "structure", "error_handling", "performance", "imports"
    title: str
    description: str
    before_snippet: Optional[str] = None
    after_snippet: Optional[str] = None


class BreakingChangeWarning(BaseModel):
    """Structured warning for potential breaking changes introduced by refactoring."""
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "signature", "api", "import_export", "return_type", "renamed_symbol", "configuration", "behavior"
    file: str
    symbol: str
    explanation: str
    suggested_mitigation: str
    affected_dependents: List[str] = Field(default_factory=list)


class RefactoredFile(BaseModel):
    """Container for a single refactored file, its diff, and associated warnings."""
    path: str
    language: str
    original_content: str
    refactored_content: str
    diff: FileDiff
    opportunities: List[ModernizationOpportunity] = Field(default_factory=list)
    warnings: List[BreakingChangeWarning] = Field(default_factory=list)
    syntax_valid: bool = True
    error: Optional[str] = None


class RiskSummary(BaseModel):
    """Aggregated risk assessment of all proposed changes."""
    overall_risk: str  # "low", "medium", "high", "critical"
    critical_warnings_count: int = 0
    high_warnings_count: int = 0
    medium_warnings_count: int = 0
    low_warnings_count: int = 0
    safety_score: int = 100  # 0 to 100
    recommendation: str = ""


class ValidationComparison(BaseModel):
    """Comparison of test execution between original and refactored code."""
    __test__ = False
    status: str  # "verified", "regressions_detected", "validation_failed", "skipped"
    original_tests_passed: int = 0
    original_tests_failed: int = 0
    refactored_tests_passed: int = 0
    refactored_tests_failed: int = 0
    regressions: List[str] = Field(default_factory=list)  # Test names that passed originally but failed now
    original_coverage_percent: Optional[float] = None
    refactored_coverage_percent: Optional[float] = None
    coverage_delta: Optional[float] = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


class RefactorResult(BaseModel):
    """Complete result of refactoring generation for a project."""
    job_id: str
    status: str  # "completed", "partial", "failed"
    total_files: int = 0
    files_modified: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    risk_summary: RiskSummary
    files: List[RefactoredFile] = Field(default_factory=list)
    all_warnings: List[BreakingChangeWarning] = Field(default_factory=list)
    all_opportunities: List[ModernizationOpportunity] = Field(default_factory=list)
    validation: Optional[ValidationComparison] = None
    error: Optional[str] = None
