"""
Refactor package — Modernization engine, AST breaking-change detection,
structured diff computation, and test validation.
"""
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
from app.refactor.diff_engine import DiffEngine, diff_engine
from app.refactor.breaking_detector import BreakingChangeDetector, breaking_change_detector
from app.refactor.validator import RefactorValidator, refactor_validator
from app.refactor.engine import RefactoringEngine, refactoring_engine

__all__ = [
    "DiffLine",
    "FileDiff",
    "ModernizationOpportunity",
    "BreakingChangeWarning",
    "RefactoredFile",
    "RiskSummary",
    "ValidationComparison",
    "RefactorResult",
    "DiffEngine",
    "diff_engine",
    "BreakingChangeDetector",
    "breaking_change_detector",
    "RefactorValidator",
    "refactor_validator",
    "RefactoringEngine",
    "refactoring_engine",
]
