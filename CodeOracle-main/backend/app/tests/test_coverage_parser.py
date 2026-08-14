"""
Phase 6 Unit Tests — Coverage parser for Python coverage.py and JS Vitest/Istanbul outputs.
"""
import os
import tempfile
import json
import pytest

from app.coverage.parser import (
    parse_python_coverage_json,
    parse_javascript_coverage_json,
    parse_coverage_file,
    _is_test_or_internal_file,
)
from app.coverage.schema import CoverageReport, FileCoverage


def test_is_test_file_filtering():
    assert _is_test_or_internal_file("generated_tests/test_calc.py") is True
    assert _is_test_or_internal_file("tests/test_server.py") is True
    assert _is_test_or_internal_file("src/utils.test.js") is True
    assert _is_test_or_internal_file("calc/__init__.py") is True
    assert _is_test_or_internal_file("calc/engine.py") is False
    assert _is_test_or_internal_file("src/validator.js") is False


def test_parse_python_coverage_json():
    raw_data = {
        "files": {
            "/tmp/workspace/calc.py": {
                "executed_lines": [1, 2, 4, 5],
                "summary": {
                    "num_statements": 6,
                    "covered_lines": 4,
                    "missing_lines": 2,
                    "percent_covered": 66.67,
                },
                "missing_lines": [7, 8],
            },
            "/tmp/workspace/generated_tests/test_calc.py": {
                "executed_lines": [1, 2],
                "summary": {"num_statements": 2, "covered_lines": 2, "percent_covered": 100},
            },
        }
    }

    report = parse_python_coverage_json(raw_data, "job-123", root_dir="/tmp/workspace")

    assert isinstance(report, CoverageReport)
    assert report.job_id == "job-123"
    assert report.language == "python"
    assert len(report.files) == 1
    assert report.files[0].path == "calc.py"
    assert report.files[0].covered_lines_count == 4
    assert report.files[0].uncovered_lines_count == 2
    assert report.files[0].coverage_percent == 66.67
    assert report.files[0].uncovered_lines == [7, 8]
    assert report.target_reached is True  # 66.67 >= 60.0


def test_parse_javascript_coverage_json():
    raw_data = {
        "total": {"lines": {"total": 10, "covered": 8, "pct": 80.0}},
        "/workspace/cart.js": {
            "lines": {"total": 10, "covered": 8, "pct": 80.0}
        },
    }

    report = parse_javascript_coverage_json(raw_data, "job-456", root_dir="/workspace")

    assert report.job_id == "job-456"
    assert report.language == "javascript"
    assert len(report.files) == 1
    assert report.files[0].path == "cart.js"
    assert report.files[0].coverage_percent == 80.0
    assert report.target_reached is True


def test_parse_coverage_file_from_disk():
    with tempfile.TemporaryDirectory() as tmp_dir:
        json_path = os.path.join(tmp_dir, "coverage.json")
        data = {
            "files": {
                "utils.py": {
                    "executed_lines": [1, 2],
                    "summary": {"num_statements": 4, "covered_lines": 2, "missing_lines": 2, "percent_covered": 50.0},
                    "missing_lines": [3, 4],
                }
            }
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        report = parse_coverage_file(json_path, "job-789", "python")
        assert report is not None
        assert report.overall_coverage_percent == 50.0
        assert report.target_reached is False  # 50 < 60
