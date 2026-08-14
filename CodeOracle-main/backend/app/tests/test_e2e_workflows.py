"""
End-to-End Workflow Integration Tests for CodeOracle
Validates the complete pipeline on Python, JavaScript, and Mixed repositories:
Upload -> Scan -> AST Analysis -> Dependency Graph -> Explanation -> Test Generation ->
Sandbox Execution -> Real Coverage -> AI Refactoring -> Risk/Breaking Detection -> Cleanup.
"""
import os
import shutil
import tempfile
import zipfile
import io
import pytest
from app.jobs.manager import JobManager
from app.ingestion.zip_handler import ZipHandler
from app.ingestion.github_handler import GitHubHandler
from app.ingestion.scanner import ProjectScanner
from app.analyzers.registry import adapter_registry
from app.graph.builder import graph_builder
from app.ai.provider import GeminiProvider
from app.ai.engine import ExplanationEngine
from app.runners.test_generator import TestGenerator
from app.runners.test_validator import test_validator
from app.runners.docker_runner import DockerRunner
from app.coverage.engine import CoverageEngine
from app.refactor.engine import RefactoringEngine
from app.refactor.validator import RefactorValidator
from app.refactor.breaking_detector import breaking_change_detector
from app.refactor.diff_engine import diff_engine


class MockAIProvider(GeminiProvider):
    """Deterministic AI provider mock for fast, offline E2E pipeline validation."""

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        prompt_lower = prompt.lower()
        if "test" in prompt_lower and "python" in prompt_lower:
            return '''
import pytest
from discount_rules import calculate_tier_discount, apply_promotional_code

def test_tier_discount():
    assert calculate_tier_discount(100.0, 1) == 5.0
    assert calculate_tier_discount(100.0, 5) == 10.0
    assert calculate_tier_discount(100.0, 50) == 20.0

def test_promo_code():
    assert apply_promotional_code("SAVE50", 100.0) == 50.0
    assert apply_promotional_code("INVALID", 100.0) == 0.0
'''
        elif "test" in prompt_lower and ("javascript" in prompt_lower or "vitest" in prompt_lower):
            return '''
import { describe, it, expect } from 'vitest';
import { validateItem } from '../validator.js';

describe('Validator tests', () => {
  it('validates items correctly', () => {
    expect(validateItem({ price: 10 })).toBe(true);
    expect(validateItem({ price: -1 })).toBe(false);
  });
});
'''
        elif "refactor" in prompt_lower and "python" in prompt_lower:
            return '''
from typing import Dict, Any, List

def calculate_tier_discount(subtotal: float, count: int) -> float:
    """Modernized calculate_tier_discount with type annotations."""
    if count > 10:
        return subtotal * 0.2
    return subtotal * 0.05 if subtotal > 100 else 0.0
'''
        elif "refactor" in prompt_lower and "javascript" in prompt_lower:
            return '''
export const formatCurrency = (amount) => {
  return `$${amount.toFixed(2)}`;
};
'''
        elif "overview" in prompt_lower:
            return "This repository provides a modular, multi-tier system with clean separation of concerns."
        else:
            return "Provides helper logic with deterministic input-output mappings and no side effects."


@pytest.fixture
def mock_ai():
    return MockAIProvider()


def create_in_memory_zip(source_dir: str) -> io.BytesIO:
    """Creates an in-memory zip archive from a source directory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zf.write(full_path, rel_path)
    buf.seek(0)
    return buf


def test_e2e_python_repository_workflow(mock_ai, tmp_path):
    """
    Full End-to-End Workflow on Python repository:
    1. ZIP packaging & safe extraction
    2. Scanner (file & line count limits)
    3. AST analysis & symbol extraction
    4. Dependency graph generation
    5. Hierarchical explanation generation
    6. Unit test generation & syntax validation
    7. Sandbox test execution & real coverage collection
    8. AI Refactoring, diffing, and breaking change detection
    9. Non-destructive guarantee check
    10. Job workspace cleanup
    """
    py_bench = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "benchmark", "python_project")
    )
    assert os.path.exists(py_bench)

    job_mgr = JobManager(base_dir=str(tmp_path / "jobs"))
    job_id = job_mgr.create_job("upload", "python_project.zip")
    job_dir = job_mgr.get_job_dir(job_id)

    # 1. Ingest via ZipHandler
    zip_bytes = create_in_memory_zip(py_bench)
    ZipHandler.extract_safely(zip_bytes, job_dir)

    # 2. Scan
    scanner = ProjectScanner(job_dir, max_lines=10000)
    scan_results = scanner.scan()
    assert scan_results["total_files"] == 3
    assert "python" in scan_results["languages"]

    # 3. Analyze AST
    project_analysis = adapter_registry.analyze_project(scan_results)
    assert len(project_analysis.files) == 3
    order_proc = next(f for f in project_analysis.files if "order_processor" in f.path)
    assert len(order_proc.classes) >= 1
    assert len(order_proc.imports) >= 1

    # 4. Dependency Graph
    dep_graph = graph_builder.build(project_analysis)
    assert dep_graph.total_nodes == 3
    assert dep_graph.total_edges >= 1

    # 5. Explanations
    explainer = ExplanationEngine(provider=mock_ai)
    explanation = explainer.explain_project(project_analysis, dep_graph)
    assert explanation.overview != ""
    assert len(explanation.files) == 3

    # 6. Test Generation & Quality Validation
    test_gen = TestGenerator(provider=mock_ai)
    gen_result = test_gen.generate_tests(project_analysis, job_dir, dep_graph)
    assert gen_result.status in ("completed", "partial")
    assert len(gen_result.generated_files) >= 1

    # Validate test code
    for gfile in gen_result.generated_files:
        if gfile.content:
            is_valid, reason = test_validator.validate_test_code(gfile.content, "python", gfile.target_file)
            assert is_valid is True, f"Validation failed: {reason}"

    # 7. Sandbox Execution & Real Coverage
    runner = DockerRunner(timeout_seconds=30, allow_local_fallback=True)
    exec_result = runner.run_tests(job_dir, language="python", framework="pytest")
    assert exec_result.status in ("passed", "failed")
    assert exec_result.total_tests >= 2

    cov_engine = CoverageEngine(provider=mock_ai, runner=runner)
    cov_report = cov_engine.measure_coverage(project_analysis, job_dir, dep_graph)
    assert cov_report.status == "completed"
    assert cov_report.total_lines > 0
    assert cov_report.overall_coverage_percent > 0.0

    # 8. Refactoring & Diff Generation
    refactor_eng = RefactoringEngine(provider=mock_ai, differ=diff_engine, detector=breaking_change_detector)
    refactor_result = refactor_eng.generate_refactor(project_analysis, job_dir, dep_graph)
    assert refactor_result.status == "completed"
    assert len(refactor_result.files) == 3
    assert refactor_result.risk_summary.safety_score >= 0

    # 9. Non-Destructive Guarantee: verify original files were not modified
    orig_discount = os.path.join(job_dir, "discount_rules.py")
    assert os.path.exists(orig_discount)
    with open(orig_discount, "r", encoding="utf-8") as f:
        orig_content = f.read()
    assert "def calculate_tier_discount" in orig_content

    # 10. Workspace cleanup
    deleted = job_mgr.delete_job(job_id)
    assert deleted is True
    assert not os.path.exists(job_dir)


def test_e2e_javascript_repository_workflow(mock_ai, tmp_path):
    """
    Full End-to-End Workflow on JavaScript repository:
    1. ZIP packaging & safe extraction
    2. Scanner & language detection
    3. JS regex-AST parsing (classes, functions, parameters, exports)
    4. Dependency graph resolution
    5. Explanation generation
    6. Test generation & JS bracket validation
    7. Refactoring proposal & breaking changes
    8. Job deletion & cleanup
    """
    js_bench = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "benchmark", "javascript_project")
    )
    assert os.path.exists(js_bench)

    job_mgr = JobManager(base_dir=str(tmp_path / "jobs"))
    job_id = job_mgr.create_job("upload", "javascript_project.zip")
    job_dir = job_mgr.get_job_dir(job_id)

    # 1. Ingestion
    zip_bytes = create_in_memory_zip(js_bench)
    ZipHandler.extract_safely(zip_bytes, job_dir)

    # 2. Scanner
    scanner = ProjectScanner(job_dir)
    scan_results = scanner.scan()
    assert scan_results["total_files"] == 3
    assert "javascript" in scan_results["languages"]

    # 3. JS Parser
    project_analysis = adapter_registry.analyze_project(scan_results)
    cart_file = next(f for f in project_analysis.files if "cart.js" in f.path)
    assert len(cart_file.classes) >= 1
    assert cart_file.classes[0].name == "CartManager"
    assert len(cart_file.classes[0].methods) >= 2

    # 4. Dependency Graph
    dep_graph = graph_builder.build(project_analysis)
    assert dep_graph.total_nodes == 3
    assert dep_graph.total_edges >= 1

    # 5. Explanations
    explainer = ExplanationEngine(provider=mock_ai)
    explanation = explainer.explain_project(project_analysis, dep_graph)
    assert explanation.overview != ""

    # 6. Test Generation & Validation
    test_gen = TestGenerator(provider=mock_ai)
    gen_result = test_gen.generate_tests(project_analysis, job_dir, dep_graph)
    assert gen_result.status in ("completed", "partial")

    for gfile in gen_result.generated_files:
        if gfile.content:
            is_valid, reason = test_validator.validate_test_code(gfile.content, "javascript", gfile.target_file)
            assert is_valid is True, f"JS test validation failed: {reason}"

    # 7. Refactoring
    refactor_eng = RefactoringEngine(provider=mock_ai)
    refactor_result = refactor_eng.generate_refactor(project_analysis, job_dir, dep_graph)
    assert refactor_result.status == "completed"

    # 8. Cleanup
    assert job_mgr.delete_job(job_id) is True
    assert not os.path.exists(job_dir)


def test_e2e_mixed_repository_workflow(mock_ai, tmp_path):
    """
    Full End-to-End Workflow on Mixed (Python + JavaScript) repository:
    1. Ingestion of dual-language project
    2. Scanner detects both 'python' and 'javascript'
    3. Dual AST analyzers run simultaneously
    4. Dependency graph builds across both languages without crashing
    5. Explanations & Refactoring work on both language components
    6. Workspace cleanup
    """
    mixed_bench = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "benchmark", "mixed_project")
    )
    assert os.path.exists(mixed_bench)

    job_mgr = JobManager(base_dir=str(tmp_path / "jobs"))
    job_id = job_mgr.create_job("upload", "mixed_project.zip")
    job_dir = job_mgr.get_job_dir(job_id)

    # 1. Ingestion
    zip_bytes = create_in_memory_zip(mixed_bench)
    ZipHandler.extract_safely(zip_bytes, job_dir)

    # 2. Scanner
    scanner = ProjectScanner(job_dir)
    scan_results = scanner.scan()
    assert len(scan_results["languages"]) == 2
    assert "python" in scan_results["languages"]
    assert "javascript" in scan_results["languages"]

    # 3. Dual AST Analysis
    project_analysis = adapter_registry.analyze_project(scan_results)
    assert len(project_analysis.files) == 4
    py_files = [f for f in project_analysis.files if f.language == "python"]
    js_files = [f for f in project_analysis.files if f.language == "javascript"]
    assert len(py_files) == 2
    assert len(js_files) == 2

    # 4. Dependency Graph
    dep_graph = graph_builder.build(project_analysis)
    assert dep_graph.total_nodes == 4
    assert dep_graph.total_edges >= 1

    # 5. Explanations
    explainer = ExplanationEngine(provider=mock_ai)
    explanation = explainer.explain_project(project_analysis, dep_graph)
    assert explanation.overview != ""
    assert len(explanation.files) == 4

    # 6. Refactoring
    refactor_eng = RefactoringEngine(provider=mock_ai)
    refactor_result = refactor_eng.generate_refactor(project_analysis, job_dir, dep_graph)
    assert refactor_result.status == "completed"
    assert len(refactor_result.files) == 4

    # 7. Cleanup
    assert job_mgr.delete_job(job_id) is True
    assert not os.path.exists(job_dir)


def test_security_zip_slip_and_limits(tmp_path):
    """
    Security verification:
    - Path traversal in ZIP archive raises PathTraversalError
    - Exceeding 10,000 lines raises LineLimitExceededError
    - Non-zip files and invalid URLs are rejected
    """
    from app.ingestion.exceptions import PathTraversalError, LineLimitExceededError, GitHubRepoError

    # 1. Zip Slip Attack
    malicious_buf = io.BytesIO()
    with zipfile.ZipFile(malicious_buf, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0::/root:/bin/bash")
    malicious_buf.seek(0)

    with pytest.raises(PathTraversalError):
        ZipHandler.extract_safely(malicious_buf, str(tmp_path / "target"))

    # 2. Line limit violation
    huge_dir = tmp_path / "huge_repo"
    huge_dir.mkdir()
    (huge_dir / "big.py").write_text("\n".join(["y = 2" for _ in range(10050)]), encoding="utf-8")

    scanner = ProjectScanner(str(huge_dir), max_lines=10000)
    with pytest.raises(LineLimitExceededError):
        scanner.scan()

    # 3. Invalid GitHub URL
    with pytest.raises(GitHubRepoError):
        GitHubHandler.download_repo("https://malicious-site.com/repo", str(tmp_path / "clone"))
