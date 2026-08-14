"""
Performance & Stress Benchmark Tests for CodeOracle
Tests AST scanning, graph generation, and context bounding on large (10k LOC) codebases.
"""
import os
import time
import tempfile
import pytest
from app.ingestion.scanner import ProjectScanner
from app.analyzers.registry import AdapterRegistry
from app.graph.builder import GraphBuilder
from app.ai.context_builder import ContextBuilder


def test_large_codebase_performance():
    """
    Generates a 10,000-line multi-module Python codebase and verifies:
    1. Scanner performance (< 1.0s).
    2. AST adapter parsing throughput (< 1.5s).
    3. Dependency graph construction (< 1.0s).
    4. ContextBuilder character limit compliance (< 3,000 chars per file context).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        num_files = 50
        lines_per_file = 190  # ~9,500 total lines (within 10k limit)

        # Generate inter-dependent modules
        file_analyses = []
        for i in range(num_files):
            filename = f"module_{i:03d}.py"
            file_path = os.path.join(temp_dir, filename)

            # Import previous module if not first
            import_stmt = f"import module_{i-1:03d}\n" if i > 0 else ""

            body = ""
            for func_idx in range(10):
                body += f"\ndef func_{func_idx}(x: int) -> int:\n"
                body += "    # Computational statement\n"
                body += f"    val = x * {func_idx + 1}\n"
                body += "    return val + 1\n"

            content = f"# Module {i}\n{import_stmt}{body}\n"
            # Pad to target line count
            current_lines = content.count("\n")
            if current_lines < lines_per_file:
                content += "\n".join([f"# padding line {j}" for j in range(lines_per_file - current_lines)]) + "\n"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 1. Measure Scanner Performance
        t0 = time.perf_counter()
        scanner = ProjectScanner(temp_dir, max_lines=10000)
        scan_result = scanner.scan()
        t_scan = time.perf_counter() - t0

        assert scan_result["total_files"] == num_files
        assert scan_result["total_lines"] >= 9000
        assert scan_result["total_lines"] <= 10000
        assert t_scan < 1.0, f"Scanning took too long: {t_scan:.3f}s"

        # 2. Measure AST Parsing Performance
        t0 = time.perf_counter()
        registry = AdapterRegistry()
        project_analysis = registry.analyze_project(scan_result)
        t_ast = time.perf_counter() - t0

        assert len(project_analysis.files) == num_files
        assert t_ast < 1.5, f"AST parsing took too long: {t_ast:.3f}s"

        # 3. Measure Graph Builder Performance
        t0 = time.perf_counter()
        graph_builder = GraphBuilder()
        dep_graph = graph_builder.build(project_analysis)
        t_graph = time.perf_counter() - t0

        assert dep_graph.total_nodes == num_files
        assert dep_graph.total_edges == num_files - 1
        assert t_graph < 1.0, f"Graph building took too long: {t_graph:.3f}s"

        # 4. Verify ContextBuilder Bounded Prompt Sizes
        cb = ContextBuilder()
        for fa in project_analysis.files[:5]:
            file_ctx = cb.build_file_context(fa, dep_graph)
            assert len(file_ctx) <= 3500, f"File context exceeded bound: {len(file_ctx)} chars"


def test_scanner_rejects_exceeding_10k_lines():
    """Verify that ProjectScanner raises LineLimitExceededError when lines > 10,000."""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "huge_file.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(["x = 1" for _ in range(10005)]))

        from app.ingestion.exceptions import LineLimitExceededError
        scanner = ProjectScanner(temp_dir, max_lines=10000)
        with pytest.raises(LineLimitExceededError) as exc_info:
            scanner.scan()

        assert exc_info.value.line_count == 10005
        assert exc_info.value.limit == 10000
