"""
Phase 7 Unit Tests — Refactoring Engine generation and non-destructive disk writes.
"""
import os
import tempfile
from unittest.mock import MagicMock
import pytest

from app.analyzers.base.schema import (
    ProjectAnalysis, FileAnalysis, FunctionSymbol
)
from app.ai.provider import GeminiProvider
from app.refactor.engine import RefactoringEngine
from app.refactor.schema import RefactorResult


def test_refactor_engine_preserves_original_and_writes_to_refactored_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        orig_file = os.path.join(tmp_dir, "service.py")
        orig_content = "def process(val):\n    return 'Result: %s' % val\n"
        with open(orig_file, "w", encoding="utf-8") as f:
            f.write(orig_content)

        fa = FileAnalysis(
            path="service.py",
            language="python",
            total_lines=2,
            functions=[FunctionSymbol(name="process", start_line=1, end_line=2)],
        )
        project = ProjectAnalysis(
            root_dir=tmp_dir,
            total_files=1,
            total_lines=2,
            languages=["python"],
            files=[fa],
        )

        mock_provider = MagicMock(spec=GeminiProvider)
        mock_provider.generate.return_value = (
            "```python\ndef process(val: str) -> str:\n    return f'Result: {val}'\n```"
        )

        engine = RefactoringEngine(provider=mock_provider)
        result = engine.generate_refactor(project, tmp_dir)

        assert isinstance(result, RefactorResult)
        assert result.status == "completed"
        assert len(result.files) == 1
        assert result.files[0].path == "service.py"
        assert result.files[0].syntax_valid is True

        # CRITICAL TEST: Verify original file was NEVER modified/overwritten
        with open(orig_file, "r", encoding="utf-8") as f:
            assert f.read() == orig_content

        # Verify refactored file was saved to {tmp_dir}/refactored/service.py
        ref_file = os.path.join(tmp_dir, "refactored", "service.py")
        assert os.path.exists(ref_file)
        with open(ref_file, "r", encoding="utf-8") as f:
            ref_content = f.read()
            assert "f'Result: {val}'" in ref_content
            assert "val: str" in ref_content
