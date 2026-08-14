"""
Test Validator — Inspects generated test files prior to disk write and execution
to reject placeholders, trivial stubs, syntax errors, and fake assertions.
"""
import re
import ast
from typing import Tuple, Optional, List


PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bplaceholder\b",
    r"implement\s+me",
    r"your\s+code\s+here",
    r"write\s+tests?\s+here",
]


class TestValidator:
    """
    Validates generated test code quality and integrity.
    """

    def validate_test_code(
        self,
        code: str,
        language: str,
        target_file: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates generated test code.
        Returns (is_valid, error_reason).
        """
        if not code or not code.strip():
            return False, "Generated test file is empty."

        clean_code = code.strip()

        # 1. Check for placeholder and TODO patterns
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, clean_code, re.IGNORECASE):
                return False, f"Generated test contains placeholder/TODO text matching '{pattern}'."

        lang = language.lower()

        if lang == "python":
            return self._validate_python_tests(clean_code, target_file)
        elif lang in ("javascript", "typescript"):
            return self._validate_javascript_tests(clean_code, target_file)

        return True, None

    def _validate_python_tests(self, code: str, target_file: str) -> Tuple[bool, Optional[str]]:
        # Check AST syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"Python syntax error in generated test: {exc.msg} at line {exc.lineno}"

        test_functions: List[ast.FunctionDef] = []
        test_classes: List[ast.ClassDef] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_") or node.name.endswith("_test"):
                    test_functions.append(node)
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("Test") or node.name.endswith("Test"):
                    test_classes.append(node)

        if not test_functions and not test_classes:
            return False, "Generated Python test file defines no 'test_*' functions or 'Test*' classes."

        # Check for non-trivial assertions
        assertions_found = 0
        trivial_assertions = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                assertions_found += 1
                # Check for `assert True` or `assert 1`
                if isinstance(node.test, ast.Constant) and node.test.value in (True, 1):
                    trivial_assertions += 1
            elif isinstance(node, ast.Call):
                # Check for pytest.raises or unittest assert calls
                if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
                    assertions_found += 1
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "raises":
                    assertions_found += 1

        if assertions_found == 0:
            return False, "Generated test file contains no assert statements or exception expectations."

        if assertions_found > 0 and assertions_found == trivial_assertions:
            return False, "Generated test file contains only trivial 'assert True' assertions."

        return True, None

    def _validate_javascript_tests(self, code: str, target_file: str) -> Tuple[bool, Optional[str]]:
        # Must contain test, it, or describe blocks
        has_blocks = re.search(r"\b(it|test|describe)\s*\(", code)
        if not has_blocks:
            return False, "Generated JavaScript test file contains no describe/test/it blocks."

        # Must contain assertions / expectations
        has_expectations = re.search(r"\b(expect|assert)\s*\(", code)
        if not has_expectations:
            return False, "Generated JavaScript test file contains no expect(...) or assert(...) statements."

        # Check for trivial assertions like expect(true).toBe(true)
        trivial_matches = len(re.findall(r"expect\s*\(\s*(true|1)\s*\)\s*\.\s*to(Be|Equal)\s*\(\s*(true|1)\s*\)", code, re.IGNORECASE))
        total_expects = len(re.findall(r"expect\s*\(", code))

        if total_expects > 0 and total_expects == trivial_matches:
            return False, "Generated JavaScript test file contains only trivial expect(true).toBe(true) assertions."

        # Bracket balancing check on stripped code
        stripped_code = _strip_js_literals_and_comments(code)
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        for ch in stripped_code:
            if ch in "({[":
                stack.append(ch)
            elif ch in ")}]":
                if not stack or stack[-1] != pairs[ch]:
                    return False, f"Unbalanced bracket/parenthesis syntax '{ch}' in JavaScript test file."
                stack.pop()

        if stack:
            return False, f"Unclosed bracket/parenthesis syntax '{stack[-1]}' in JavaScript test file."

        return True, None


def _strip_js_literals_and_comments(code: str) -> str:
    """Removes string literals ('', "", ``) and comments (//, /* */) to avoid false bracket balance mismatches."""
    result = []
    i = 0
    n = len(code)
    in_block_comment = False

    while i < n:
        if in_block_comment:
            if code[i:i+2] == "*/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if code[i:i+2] == "/*":
            in_block_comment = True
            i += 2
            continue

        if code[i:i+2] == "//":
            while i < n and code[i] != "\n":
                i += 1
            continue

        ch = code[i]
        if ch in ('"', "'", '`'):
            quote = ch
            i += 1
            while i < n:
                if code[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                if code[i] == quote:
                    i += 1
                    break
                i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


# Global singleton
test_validator = TestValidator()

