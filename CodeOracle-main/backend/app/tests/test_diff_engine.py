"""
Phase 7 Unit Tests — Diff Engine line-by-line and summary calculation.
"""
import pytest
from app.refactor.diff_engine import DiffEngine


def test_diff_engine_identical_files():
    engine = DiffEngine()
    orig = "def add(a, b):\n    return a + b\n"
    diff = engine.compute_diff("math_ops.py", orig, orig)

    assert diff.path == "math_ops.py"
    assert diff.additions == 0
    assert diff.deletions == 0
    assert diff.modifications == 0
    assert len(diff.diff_lines) == 2
    assert all(l.type == "same" for l in diff.diff_lines)


def test_diff_engine_additions_and_deletions():
    engine = DiffEngine()
    orig = "def greet(name):\n    print('Hello %s' % name)\n"
    refactored = "def greet(name: str) -> None:\n    # Log message\n    print(f'Hello {name}')\n"

    diff = engine.compute_diff("greet.py", orig, refactored)

    assert diff.path == "greet.py"
    assert diff.additions > 0 or diff.modifications > 0
    assert len(diff.diff_lines) > 0
    assert "--- a/greet.py" in diff.diff_text or "+++ b/greet.py" in diff.diff_text
