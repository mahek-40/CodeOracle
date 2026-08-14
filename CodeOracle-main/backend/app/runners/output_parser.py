"""
Parses test runner terminal outputs (pytest, Vitest, Jest) into structured test results.
"""
import re
from typing import List, Tuple
from app.runners.schema import TestCaseResult


def parse_pytest_output(
    stdout: str,
    stderr: str,
    exit_code: int,
) -> Tuple[int, int, int, int, List[TestCaseResult]]:
    """
    Parses standard pytest -v terminal output.
    Returns (total_tests, passed_tests, failed_tests, skipped_tests, test_cases).
    """
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    test_cases: List[TestCaseResult] = []

    combined = stdout + "\n" + stderr

    # 1. Parse individual test items (pytest -v format: path/to/test.py::test_name STATUS)
    item_pattern = re.compile(r"^(.*?::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)", re.MULTILINE)
    for match in item_pattern.finditer(stdout):
        test_name = match.group(1).strip()
        status_raw = match.group(2).strip().lower()
        status = "passed" if status_raw == "passed" else ("failed" if status_raw in ("failed", "error") else "skipped")
        test_cases.append(TestCaseResult(name=test_name, status=status))

    # 2. Parse summary line (e.g. "== 5 passed, 1 failed, 2 skipped in 0.35s ==")
    # Look for patterns like: "5 passed", "1 failed", "2 skipped", "1 error"
    passed_match = re.search(r"(\d+)\s+passed", combined)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"(\d+)\s+failed", combined)
    if failed_match:
        failed = int(failed_match.group(1))

    skipped_match = re.search(r"(\d+)\s+skipped", combined)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    error_match = re.search(r"(\d+)\s+error", combined)
    if error_match:
        errors = int(error_match.group(1))
        failed += errors

    # If test cases were extracted but summary regex missed
    if passed == 0 and failed == 0 and skipped == 0 and test_cases:
        passed = sum(1 for t in test_cases if t.status == "passed")
        failed = sum(1 for t in test_cases if t.status in ("failed", "error"))
        skipped = sum(1 for t in test_cases if t.status == "skipped")

    total = passed + failed + skipped
    return total, passed, failed, skipped, test_cases


def parse_vitest_output(
    stdout: str,
    stderr: str,
    exit_code: int,
) -> Tuple[int, int, int, int, List[TestCaseResult]]:
    """
    Parses Vitest / Jest terminal output.
    Returns (total_tests, passed_tests, failed_tests, skipped_tests, test_cases).
    """
    passed = 0
    failed = 0
    skipped = 0
    test_cases: List[TestCaseResult] = []

    combined = stdout + "\n" + stderr

    # Vitest format: "Tests  4 passed (4)" or "Tests  1 failed | 3 passed (4)"
    # Jest format: "Tests:       1 failed, 3 passed, 4 total"
    vitest_tests_line = re.search(r"Tests\s+(.*?)(?:\n|$)", combined)
    if vitest_tests_line:
        line = vitest_tests_line.group(1)
        p_match = re.search(r"(\d+)\s+passed", line)
        if p_match:
            passed = int(p_match.group(1))
        f_match = re.search(r"(\d+)\s+failed", line)
        if f_match:
            failed = int(f_match.group(1))
        s_match = re.search(r"(\d+)\s+skipped", line)
        if s_match:
            skipped = int(s_match.group(1))

    # Parse individual checkmark lines (✓ test name or ✕ test name)
    item_pattern = re.compile(r"^\s*([✓✕✗]|PASS|FAIL)\s+(.*?)$", re.MULTILINE)
    for match in item_pattern.finditer(stdout):
        symbol = match.group(1).strip()
        name = match.group(2).strip()
        status = "passed" if symbol in ("✓", "PASS") else "failed"
        test_cases.append(TestCaseResult(name=name, status=status))

    if passed == 0 and failed == 0 and skipped == 0 and test_cases:
        passed = sum(1 for t in test_cases if t.status == "passed")
        failed = sum(1 for t in test_cases if t.status == "failed")

    total = passed + failed + skipped
    return total, passed, failed, skipped, test_cases


def parse_test_output(
    framework: str,
    stdout: str,
    stderr: str,
    exit_code: int,
) -> Tuple[int, int, int, int, List[TestCaseResult]]:
    """Dispatches to the appropriate runner parser."""
    if framework.lower() in ("pytest", "python"):
        return parse_pytest_output(stdout, stderr, exit_code)
    elif framework.lower() in ("vitest", "jest", "javascript", "node"):
        return parse_vitest_output(stdout, stderr, exit_code)
    else:
        return parse_pytest_output(stdout, stderr, exit_code)
