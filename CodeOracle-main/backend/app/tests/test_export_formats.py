"""
Unit and integration tests for Phase 8 export formats, schemas, and end-to-end data contracts.
"""
import pytest
from app.graph.schema import GraphNode, GraphEdge, DependencyGraph
from app.ai.schema import ProjectExplanation, FileExplanation, SymbolExplanation
from app.coverage.schema import CoverageReport, FileCoverage
from app.refactor.schema import (
    RefactorResult,
    RefactoredFile,
    FileDiff,
    DiffLine,
    BreakingChangeWarning,
    ModernizationOpportunity,
    RiskSummary,
)


def test_explanation_export_contract():
    """Verify that ProjectExplanation contains all expected fields for markdown report export."""
    sym = SymbolExplanation(
        name="calculate_total",
        symbol_type="function",
        start_line=10,
        end_line=25,
        summary="Calculates order subtotal minus discounts.",
        file_path="order_processor.py",
    )
    fe = FileExplanation(
        path="order_processor.py",
        language="python",
        total_lines=50,
        summary="Processes customer orders and applies tiered discounts.",
        key_exports=["OrderProcessor"],
        dependencies=["discount_rules.py"],
        symbols=[sym],
    )
    explanation = ProjectExplanation(
        overview="E-commerce order calculation and billing service.",
        languages=["python"],
        total_files=1,
        total_lines=50,
        entry_points=["order_processor.py"],
        files=[fe],
        partial=False,
    )

    assert explanation.overview == "E-commerce order calculation and billing service."
    assert len(explanation.files) == 1
    assert explanation.files[0].symbols[0].name == "calculate_total"
    assert explanation.files[0].dependencies == ["discount_rules.py"]


def test_dependency_graph_export_contract():
    """Verify that DependencyGraph schema matches export specifications."""
    node1 = GraphNode(
        id="order_processor.py",
        path="order_processor.py",
        label="order_processor.py",
        language="python",
        total_lines=50,
        num_functions=2,
        num_classes=1,
        num_imports=1,
        num_exports=1,
    )
    node2 = GraphNode(
        id="discount_rules.py",
        path="discount_rules.py",
        label="discount_rules.py",
        language="python",
        total_lines=30,
        num_functions=1,
        num_classes=0,
        num_imports=0,
        num_exports=1,
    )
    edge = GraphEdge(
        id="e1",
        source="order_processor.py",
        target="discount_rules.py",
        module="discount_rules",
    )

    graph = DependencyGraph(
        nodes=[node1, node2],
        edges=[edge],
        total_nodes=2,
        total_edges=1,
        dependencies_map={"order_processor.py": ["discount_rules.py"]},
        dependents_map={"discount_rules.py": ["order_processor.py"]},
    )

    assert graph.total_nodes == 2
    assert graph.dependencies_map["order_processor.py"] == ["discount_rules.py"]
    assert graph.dependents_map["discount_rules.py"] == ["order_processor.py"]


def test_refactor_patch_export_contract():
    """Verify that RefactorResult schema generates structured diff lines and risk summary."""
    diff_line = DiffLine(
        type="mod",
        orig_line_num=1,
        refactored_line_num=1,
        content="- def calculate_discount(price):\n+ def calculate_discount(price: float) -> float:",
    )
    file_diff = FileDiff(
        path="discount_rules.py",
        additions=1,
        deletions=1,
        modifications=1,
        diff_text="--- discount_rules.py\n+++ discount_rules.py\n@@ -1,1 +1,1 @@\n- def calculate_discount(price):\n+ def calculate_discount(price: float) -> float:",
        diff_lines=[diff_line],
    )
    warning = BreakingChangeWarning(
        severity="low",
        category="signature",
        file="discount_rules.py",
        symbol="calculate_discount",
        explanation="Added explicit type annotations.",
        suggested_mitigation="Verify callers pass valid floats.",
        affected_dependents=["order_processor.py"],
    )
    opp = ModernizationOpportunity(
        category="types",
        title="Added Python 3.10+ type annotations",
        description="Replaced untyped signature with float annotations.",
    )
    risk = RiskSummary(
        overall_risk="low",
        critical_warnings_count=0,
        high_warnings_count=0,
        medium_warnings_count=0,
        low_warnings_count=1,
        safety_score=95,
        recommendation="Safe to apply modernization.",
    )
    refactored_file = RefactoredFile(
        path="discount_rules.py",
        language="python",
        original_content="def calculate_discount(price):\n    return price * 0.1\n",
        refactored_content="def calculate_discount(price: float) -> float:\n    return price * 0.1\n",
        diff=file_diff,
        opportunities=[opp],
        warnings=[warning],
        syntax_valid=True,
    )
    result = RefactorResult(
        job_id="job-123",
        status="completed",
        total_files=1,
        files_modified=1,
        total_additions=1,
        total_deletions=1,
        risk_summary=risk,
        files=[refactored_file],
        all_warnings=[warning],
        all_opportunities=[opp],
    )

    assert result.risk_summary.safety_score == 95
    assert len(result.files) == 1
    assert result.files[0].diff.additions == 1
    assert "--- discount_rules.py" in result.files[0].diff.diff_text
