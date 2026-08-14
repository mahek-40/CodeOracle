"""
Comprehensive integration tests for the test execution, dependency management,
test validator, and multi-format coverage collection pipeline.
"""
import os
import sys
import shutil
import pytest
from app.runners.dependency_manager import DependencyManager, dependency_manager
from app.runners.test_validator import TestValidator, test_validator
from app.coverage.parser import (
    parse_python_coverage_json,
    parse_python_coverage_xml,
    parse_javascript_coverage_json,
    parse_javascript_lcov,
    parse_coverage_file,
)
from app.coverage.engine import CoverageEngine
from app.runners.docker_runner import DockerRunner
from app.analyzers.registry import adapter_registry
from app.ingestion.scanner import ProjectScanner
from app.graph.builder import graph_builder


def test_dependency_manager_detects_manifests(tmp_path):
    """Verifies that DependencyManager detects requirements.txt, pyproject.toml, and package.json across directories."""
    # Create Python structure
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "requirements.txt").write_text("pytest\ncoverage\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n", encoding="utf-8")

    # Create JS structure
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text('{"name": "client"}', encoding="utf-8")

    dm = DependencyManager()
    py_manifests = dm.detect_dependencies(str(tmp_path), "python")
    assert len(py_manifests) == 2
    types = [m["type"] for m in py_manifests]
    assert "requirements.txt" in types
    assert "pyproject.toml" in types

    js_manifests = dm.detect_dependencies(str(tmp_path), "javascript")
    assert len(js_manifests) == 1
    assert js_manifests[0]["type"] == "package.json"
    assert js_manifests[0]["rel_dir"] == "frontend"


def test_test_validator_rejects_placeholders_and_trivial_assertions():
    """Verifies that TestValidator rejects TODOs, placeholders, and trivial assert True stubs."""
    validator = TestValidator()

    # 1. Reject TODO comments
    code_with_todo = """
import pytest
from utils import add

def test_add():
    # TODO: implement test cases here
    pass
"""
    is_valid, reason = validator.validate_test_code(code_with_todo, "python", "utils.py")
    assert is_valid is False
    assert "placeholder/TODO" in reason

    # 2. Reject trivial assert True
    trivial_python = """
import pytest

def test_something():
    assert True
"""
    is_valid, reason = validator.validate_test_code(trivial_python, "python", "calc.py")
    assert is_valid is False
    assert "trivial" in reason

    # 3. Reject trivial JS expect(true).toBe(true)
    trivial_js = """
import { describe, it, expect } from 'vitest';

describe('suite', () => {
  it('works', () => {
    expect(true).toBe(true);
  });
});
"""
    is_valid, reason = validator.validate_test_code(trivial_js, "javascript", "calc.js")
    assert is_valid is False
    assert "trivial" in reason

    # 4. Accept meaningful Python test
    valid_python = """
import pytest
from calc import multiply

def test_multiply_numbers():
    result = multiply(3, 4)
    assert result == 12

def test_multiply_zero():
    assert multiply(5, 0) == 0
"""
    is_valid, reason = validator.validate_test_code(valid_python, "python", "calc.py")
    assert is_valid is True
    assert reason is None


def test_coverage_xml_parser_calculates_exact_percentages():
    """Verifies that parse_python_coverage_xml extracts exact statement counts and line hits."""
    cobertura_xml = """<?xml version="1.0" ?>
<coverage version="7.0" timestamp="1600000000" lines-valid="10" lines-covered="8" line-rate="0.8">
  <packages>
    <package name="app" line-rate="0.8">
      <classes>
        <class name="calculator.py" filename="calculator.py" line-rate="0.8">
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="1"/>
            <line number="3" hits="1"/>
            <line number="4" hits="0"/>
            <line number="5" hits="1"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""
    report = parse_python_coverage_xml(cobertura_xml, "job_test_xml")
    assert report is not None
    assert report.total_lines == 5
    assert report.total_covered_lines == 4
    assert report.total_uncovered_lines == 1
    assert report.overall_coverage_percent == 80.0
    assert report.status == "completed"
    assert len(report.files) == 1
    assert report.files[0].path == "calculator.py"
    assert report.files[0].covered_lines == [1, 2, 3, 5]
    assert report.files[0].uncovered_lines == [4]


def test_coverage_lcov_parser_calculates_exact_percentages():
    """Verifies that parse_javascript_lcov parses Vitest/Istanbul lcov.info format accurately."""
    lcov_text = """SF:src/formatter.js
DA:1,1
DA:2,1
DA:3,0
DA:4,1
end_of_record
"""
    report = parse_javascript_lcov(lcov_text, "job_test_lcov")
    assert report is not None
    assert report.total_lines == 4
    assert report.total_covered_lines == 3
    assert report.total_uncovered_lines == 1
    assert report.overall_coverage_percent == 75.0
    assert report.status == "completed"
    assert len(report.files) == 1
    assert report.files[0].path == "src/formatter.js"
    assert report.files[0].covered_lines == [1, 2, 4]
    assert report.files[0].uncovered_lines == [3]


def test_real_test_execution_and_coverage_on_python_benchmark(tmp_path):
    """
    End-to-end integration test:
    Scans real python benchmark repository, generates valid tests, executes test runner,
    collects genuine coverage, and asserts coverage > 0%.
    """
    benchmark_src = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "benchmark", "python_project")
    )
    assert os.path.exists(benchmark_src)

    # Copy benchmark to isolated tmp workspace
    job_dir = tmp_path / "job_bench_py"
    shutil.copytree(benchmark_src, str(job_dir))

    # Scan and analyze
    scanner = ProjectScanner(str(job_dir))
    scan_results = scanner.scan()
    project = adapter_registry.analyze_project(scan_results)

    # Create generated tests folder and write a valid pytest test for discount_rules
    tests_dir = job_dir / "generated_tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    test_code = """
import pytest
from discount_rules import calculate_tier_discount, apply_promotional_code, is_vip_customer

def test_calculate_tier_discount_100():
    discount = calculate_tier_discount(100.0, 1)
    assert discount == 5.0

def test_calculate_tier_discount_bulk():
    discount = calculate_tier_discount(100.0, 20)
    assert discount == 15.0

def test_promotional_code():
    assert apply_promotional_code("SAVE50", 100.0) == 50.0
    assert apply_promotional_code("INVALID", 100.0) == 0.0

def test_vip_customer():
    assert is_vip_customer(3000.0, 24) is True
    assert is_vip_customer(100.0, 1) is False
"""
    (tests_dir / "test_discount_rules.py").write_text(test_code, encoding="utf-8")

    # Run tests using DockerRunner with fallback support
    runner = DockerRunner(timeout_seconds=30, allow_local_fallback=True)
    result = runner.run_tests(str(job_dir), language="python", framework="pytest")

    assert result.status == "passed"
    assert result.total_tests >= 4
    assert result.passed_tests >= 4
    assert result.failed_tests == 0
    assert result.exit_code == 0

    # Verify coverage report was generated and parsed
    assert result.coverage_report is not None
    assert result.coverage_report.status == "completed"
    assert result.coverage_report.total_lines > 0
    assert result.coverage_report.total_covered_lines > 0
    assert result.coverage_report.overall_coverage_percent > 0.0

    # Ensure coverage report matches discount_rules.py
    disc_file = next((f for f in result.coverage_report.files if "discount_rules" in f.path), None)
    assert disc_file is not None
    assert disc_file.coverage_percent > 0.0
    assert disc_file.covered_lines_count > 0


def test_measure_coverage_returns_failure_when_execution_fails(tmp_path):
    """Verifies that CoverageEngine returns explicit failed report instead of fake 0% when execution fails."""
    job_dir = tmp_path / "broken_job"
    job_dir.mkdir(exist_ok=True)
    tests_dir = job_dir / "generated_tests"
    tests_dir.mkdir(exist_ok=True)

    # Write a test that fails on import of nonexistent package
    broken_test = """
import nonexistent_uninstalled_module_12345

def test_fail():
    assert True
"""
    (tests_dir / "test_broken.py").write_text(broken_test, encoding="utf-8")

    scanner = ProjectScanner(str(job_dir))
    scan_results = scanner.scan()
    project = adapter_registry.analyze_project(scan_results)

    runner = DockerRunner(timeout_seconds=30, allow_local_fallback=True)
    engine = CoverageEngine(runner=runner)
    report = engine.measure_coverage(project, str(job_dir))

    assert report.status == "failed"
    assert report.stage in ("test_execution", "coverage_collection")
    assert report.error is not None
    assert len(report.files) == 0  # No fake files list
