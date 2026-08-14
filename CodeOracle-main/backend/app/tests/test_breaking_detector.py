"""
Phase 7 Unit Tests — AST Breaking Change Detector.
"""
import pytest
from app.analyzers.base.schema import (
    FileAnalysis, FunctionSymbol, ParameterSymbol, ClassSymbol
)
from app.graph.schema import DependencyGraph, GraphNode, GraphEdge
from app.refactor.breaking_detector import BreakingChangeDetector


def test_detect_removed_public_function():
    orig_fa = FileAnalysis(
        path="payment.py",
        language="python",
        total_lines=20,
        functions=[
            FunctionSymbol(name="charge_card", start_line=1, end_line=10),
            FunctionSymbol(name="refund_transaction", start_line=11, end_line=20),
        ],
    )

    # In refactored code, refund_transaction was dropped
    ref_fa = FileAnalysis(
        path="payment.py",
        language="python",
        total_lines=15,
        functions=[
            FunctionSymbol(name="charge_card", start_line=1, end_line=10),
        ],
    )

    graph = DependencyGraph(
        nodes=[
            GraphNode(
                id="payment.py",
                label="payment.py",
                path="payment.py",
                language="python",
                total_lines=20,
                num_functions=2,
                num_classes=0,
                num_imports=0,
                num_exports=2,
            )
        ],
        edges=[
            GraphEdge(
                id="e1",
                source="checkout.py",
                target="payment.py",
                module="payment",
                is_relative=True,
            )
        ],
    )

    detector = BreakingChangeDetector()
    warnings = detector.detect_breaking_changes(orig_fa, ref_fa, graph)

    assert len(warnings) == 1
    w = warnings[0]
    assert w.symbol == "refund_transaction"
    assert w.severity == "critical"  # Elevated because checkout.py depends on payment.py
    assert "checkout.py" in w.affected_dependents


def test_detect_added_required_parameter():
    orig_fa = FileAnalysis(
        path="tax.py",
        language="python",
        total_lines=10,
        functions=[
            FunctionSymbol(
                name="calc_tax",
                start_line=1,
                end_line=5,
                parameters=[ParameterSymbol(name="amount", type_annotation="float")],
            )
        ],
    )

    # In refactored code, new parameter state_code was added
    ref_fa = FileAnalysis(
        path="tax.py",
        language="python",
        total_lines=10,
        functions=[
            FunctionSymbol(
                name="calc_tax",
                start_line=1,
                end_line=5,
                parameters=[
                    ParameterSymbol(name="amount", type_annotation="float"),
                    ParameterSymbol(name="state_code", type_annotation="str"),
                ],
            )
        ],
    )

    detector = BreakingChangeDetector()
    warnings = detector.detect_breaking_changes(orig_fa, ref_fa)

    assert len(warnings) == 1
    assert warnings[0].category == "signature"
    assert "calc_tax" in warnings[0].symbol


def test_detect_removed_class():
    orig_fa = FileAnalysis(
        path="models.py",
        language="python",
        total_lines=30,
        classes=[
            ClassSymbol(name="UserSession", start_line=1, end_line=20),
        ],
    )
    ref_fa = FileAnalysis(
        path="models.py",
        language="python",
        total_lines=15,
        classes=[],
    )

    detector = BreakingChangeDetector()
    warnings = detector.detect_breaking_changes(orig_fa, ref_fa)

    assert len(warnings) == 1
    assert warnings[0].symbol == "UserSession"
    assert warnings[0].category == "renamed_symbol"
