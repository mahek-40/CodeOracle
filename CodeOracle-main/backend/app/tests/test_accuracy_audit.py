"""
Accuracy & Reliability Audit Test Suite.
Validates exact line numbers, AST class method parsing, parent relative import resolution,
folder index candidate matching, parameter default handling in breaking change detection,
and dual-language project analysis.
"""
import os
import io
import zipfile
import pytest
from app.analyzers.python.adapter import PythonAdapter
from app.analyzers.javascript.adapter import JavaScriptAdapter
from app.analyzers.registry import adapter_registry
from app.analyzers.base.schema import (
    FileAnalysis,
    FunctionSymbol,
    ClassSymbol,
    ParameterSymbol,
    ImportSymbol,
    ProjectAnalysis,
)
from app.graph.builder import graph_builder
from app.ingestion.scanner import ProjectScanner
from app.ingestion.zip_handler import ZipHandler
from app.refactor.breaking_detector import breaking_change_detector


def test_javascript_adapter_accurate_line_bounds_and_methods(tmp_path):
    """Verifies that JavaScriptAdapter computes genuine line numbers and parses class methods."""
    js_code = """import { helper } from './utils.js';

export class OrderService {
  constructor(apiClient, timeout = 5000) {
    this.client = apiClient;
    this.timeout = timeout;
  }

  async processOrder(orderId, notifyUser = true) {
    const res = await this.client.send(orderId);
    return res.data;
  }

  cancelOrder(orderId) {
    return this.client.cancel(orderId);
  }
}

export function standaloneCalc(a, b = 10) {
  const sum = a + b;
  return sum;
}
"""
    file_path = tmp_path / "order_service.js"
    file_path.write_text(js_code, encoding="utf-8")

    adapter = JavaScriptAdapter()
    analysis = adapter.parse_file(str(file_path), "order_service.js")

    assert analysis.language == "javascript"
    assert len(analysis.classes) == 1
    cls = analysis.classes[0]
    assert cls.name == "OrderService"
    assert cls.start_line == 3
    # Check that end_line is genuine matching brace line (> 10)
    assert cls.end_line >= 16

    # Verify class methods
    method_names = [m.name for m in cls.methods]
    assert "constructor" in method_names
    assert "processOrder" in method_names
    assert "cancelOrder" in method_names

    # Verify method parameters and defaults
    proc_method = next(m for m in cls.methods if m.name == "processOrder")
    assert proc_method.is_async is True
    assert len(proc_method.parameters) == 2
    assert proc_method.parameters[0].name == "orderId"
    assert proc_method.parameters[1].name == "notifyUser"
    assert proc_method.parameters[1].default_value == "true"

    # Verify standalone function
    assert len(analysis.functions) == 1
    fn = analysis.functions[0]
    assert fn.name == "standaloneCalc"
    assert len(fn.parameters) == 2
    assert fn.parameters[1].default_value == "10"


def test_dependency_graph_resolves_parent_and_relative_imports():
    """Verifies that GraphBuilder handles ../ parent traversal, ./ relative paths, and index files."""
    files = [
        FileAnalysis(
            path="src/components/Button.tsx",
            language="javascript",
            total_lines=20,
            imports=[
                ImportSymbol(module="../utils/helper", line=1, is_relative=True),
                ImportSymbol(module="../services", line=2, is_relative=True),
            ],
        ),
        FileAnalysis(
            path="src/utils/helper.ts",
            language="javascript",
            total_lines=15,
            imports=[],
        ),
        FileAnalysis(
            path="src/services/index.ts",
            language="javascript",
            total_lines=30,
            imports=[],
        ),
        FileAnalysis(
            path="backend/api/routes.py",
            language="python",
            total_lines=40,
            imports=[
                ImportSymbol(module="models", names=["User"], line=1, is_relative=True, level=1),
                ImportSymbol(module="core.config", names=["settings"], line=2, is_relative=True, level=2),
            ],
        ),
        FileAnalysis(
            path="backend/api/models.py",
            language="python",
            total_lines=25,
            imports=[],
        ),
        FileAnalysis(
            path="backend/core/config.py",
            language="python",
            total_lines=18,
            imports=[],
        ),
    ]

    project = ProjectAnalysis(
        root_dir="/workspace",
        total_files=len(files),
        total_lines=sum(f.total_lines for f in files),
        languages=["javascript", "python"],
        files=files,
    )

    graph = graph_builder.build(project)

    # Check edges
    edge_pairs = [(e.source, e.target) for e in graph.edges]

    # JS parent relative import: Button -> helper.ts
    assert ("src/components/Button.tsx", "src/utils/helper.ts") in edge_pairs
    # JS folder import: Button -> services/index.ts
    assert ("src/components/Button.tsx", "src/services/index.ts") in edge_pairs
    # Python dot level=1: routes.py -> models.py
    assert ("backend/api/routes.py", "backend/api/models.py") in edge_pairs
    # Python dot level=2: routes.py -> config.py
    assert ("backend/api/routes.py", "backend/core/config.py") in edge_pairs

    # Verify no self-loops or hallucinated targets
    for source, target in edge_pairs:
        assert source != target
        assert any(f.path == target for f in files)


def test_breaking_change_detector_differentiates_required_vs_optional_params():
    """Verifies that optional parameter additions with defaults are low risk, while missing defaults are critical."""
    orig_fn = FunctionSymbol(
        name="calculate_tax",
        parameters=[ParameterSymbol(name="amount")],
        start_line=1,
        end_line=5,
    )

    # 1. Non-breaking: added parameter with default value
    ref_fn_safe = FunctionSymbol(
        name="calculate_tax",
        parameters=[
            ParameterSymbol(name="amount"),
            ParameterSymbol(name="discount", default_value="0.0"),
        ],
        start_line=1,
        end_line=5,
    )

    orig_fa = FileAnalysis(path="tax.py", language="python", total_lines=10, functions=[orig_fn])
    ref_fa_safe = FileAnalysis(path="tax.py", language="python", total_lines=10, functions=[ref_fn_safe])

    safe_warnings = breaking_change_detector.detect_breaking_changes(orig_fa, ref_fa_safe)
    assert len(safe_warnings) == 1
    assert safe_warnings[0].severity == "low"

    # 2. Breaking: added parameter without default value
    ref_fn_breaking = FunctionSymbol(
        name="calculate_tax",
        parameters=[
            ParameterSymbol(name="amount"),
            ParameterSymbol(name="mandatory_rule", default_value=None),
        ],
        start_line=1,
        end_line=5,
    )
    ref_fa_breaking = FileAnalysis(path="tax.py", language="python", total_lines=10, functions=[ref_fn_breaking])

    breaking_warnings = breaking_change_detector.detect_breaking_changes(orig_fa, ref_fa_breaking)
    assert len(breaking_warnings) == 1
    assert breaking_warnings[0].severity in ("critical", "high")


def test_zip_handler_flattens_nested_archive(tmp_path):
    """Verifies that ZipHandler flattens archives that contain a single top-level folder."""
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("my-project-main/src/main.py", "print('hello')\n")
        zf.writestr("my-project-main/src/utils.py", "def add(a, b): return a + b\n")
    zip_bytes.seek(0)

    target_dir = tmp_path / "extracted"
    os.makedirs(target_dir, exist_ok=True)

    ZipHandler.extract_safely(zip_bytes, str(target_dir))

    # Expect src/ to be directly under target_dir, not under my-project-main/
    assert os.path.exists(target_dir / "src" / "main.py")
    assert os.path.exists(target_dir / "src" / "utils.py")
    assert not os.path.exists(target_dir / "my-project-main")


def test_mixed_benchmark_project_scanning_and_analysis():
    """Verifies that the mixed project benchmark is accurately scanned and analyzed."""
    benchmark_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "benchmark", "mixed_project")
    )
    assert os.path.exists(benchmark_dir)

    scanner = ProjectScanner(benchmark_dir)
    scan_results = scanner.scan()

    assert scan_results["total_files"] >= 4
    assert "python" in scan_results["languages"]
    assert "javascript" in scan_results["languages"]

    analysis = adapter_registry.analyze_project(scan_results)
    assert len(analysis.files) >= 4

    graph = graph_builder.build(analysis)
    assert graph.total_nodes >= 4
    # Expect edges in both Python and JS
    edge_pairs = [(e.source, e.target) for e in graph.edges]
    assert ("backend_service.py", "auth_helper.py") in edge_pairs
    assert ("client_api.js", "formatter.js") in edge_pairs
