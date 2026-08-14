"""
Phase 5 Unit Tests — Test generation pipeline, prompt builders, code extraction, and mock generation.
No live Gemini calls needed.
"""
import os
import tempfile
from unittest.mock import MagicMock
import pytest

from app.ai.test_prompts import python_test_generation_prompt, javascript_test_generation_prompt
from app.ai.provider import GeminiProvider, AIKeyMissingError, AIQuotaError
from app.analyzers.base.schema import (
    ProjectAnalysis, FileAnalysis, FunctionSymbol, ParameterSymbol, ClassSymbol
)
from app.runners.test_generator import (
    TestGenerator, _clean_code_blocks, _estimate_test_count, _derive_module_name
)
from app.runners.schema import TestGenerationResult


def test_clean_code_blocks():
    """Verify markdown code fences are stripped cleanly."""
    raw1 = "```python\ndef test_add():\n    assert 1 + 1 == 2\n```"
    assert _clean_code_blocks(raw1) == "def test_add():\n    assert 1 + 1 == 2"

    raw2 = "```javascript\ndescribe('test', () => {});\n```"
    assert _clean_code_blocks(raw2) == "describe('test', () => {});"

    raw3 = "def test_raw():\n    pass"
    assert _clean_code_blocks(raw3) == "def test_raw():\n    pass"


def test_estimate_test_count():
    """Verify test counts are counted accurately for Python and JS."""
    py_code = """
def test_one():
    pass

def test_two():
    pass

class TestSuite:
    def test_three(self):
        pass
"""
    assert _estimate_test_count(py_code, "python") == 3

    js_code = """
describe('Math', () => {
    it('adds numbers', () => {});
    test('subtracts numbers', () => {});
});
"""
    assert _estimate_test_count(js_code, "javascript") == 2


def test_derive_module_name():
    assert _derive_module_name("calculator.py") == "calculator"
    assert _derive_module_name("src/utils/math.py") == "src.utils.math"
    assert _derive_module_name("app/server.js") == "app.server"


def test_prompt_builders():
    py_prompt = python_test_generation_prompt("server.py", "Context info", "server")
    assert "pytest" in py_prompt
    assert "server.py" in py_prompt
    assert "Context info" in py_prompt

    js_prompt = javascript_test_generation_prompt("app.js", "JS Context", "./app.js", "vitest")
    assert "vitest" in js_prompt
    assert "app.js" in js_prompt


def test_test_generator_python_project():
    """Test generating pytest files for a Python project with mocked provider."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.generate.return_value = """```python
import pytest
from calc import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_zero():
    assert add(0, 0) == 0
```"""

    fa = FileAnalysis(
        path="calc.py",
        language="python",
        total_lines=10,
        functions=[FunctionSymbol(name="add", start_line=1, end_line=3,
                                  parameters=[ParameterSymbol(name="a"), ParameterSymbol(name="b")])],
    )
    pa = ProjectAnalysis(
        root_dir="/tmp/test",
        total_files=1,
        total_lines=10,
        languages=["python"],
        files=[fa],
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        generator = TestGenerator(provider=mock_provider)
        result = generator.generate_tests(pa, tmp_dir)

        assert isinstance(result, TestGenerationResult)
        assert result.status == "completed"
        assert result.framework == "pytest"
        assert len(result.generated_files) == 1

        gen_file = result.generated_files[0]
        assert gen_file.filename == "test_calc.py"
        assert gen_file.target_file == "calc.py"
        assert gen_file.num_tests_estimated == 2
        assert "def test_add_positive" in gen_file.content

        # Verify file written to disk
        written_path = os.path.join(tmp_dir, "generated_tests", "test_calc.py")
        assert os.path.exists(written_path)
        with open(written_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "def test_add_positive" in content

        # Verify manifest
        manifest_path = os.path.join(tmp_dir, "generated_tests", "manifest.json")
        assert os.path.exists(manifest_path)


def test_test_generator_handles_gemini_error():
    """Verify generator handles provider failure gracefully."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.generate.side_effect = AIQuotaError("Quota exceeded")

    fa = FileAnalysis(
        path="server.py",
        language="python",
        total_lines=10,
        functions=[FunctionSymbol(name="run", start_line=1, end_line=5)],
    )
    pa = ProjectAnalysis(
        root_dir="/tmp/test",
        total_files=1,
        total_lines=10,
        languages=["python"],
        files=[fa],
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        generator = TestGenerator(provider=mock_provider)
        result = generator.generate_tests(pa, tmp_dir)

        assert result.status == "failed"
        assert len(result.generated_files) == 1
        assert result.generated_files[0].error is not None
        assert "Quota exceeded" in result.generated_files[0].error
