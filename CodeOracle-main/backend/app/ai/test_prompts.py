"""
Test generation prompts — structured prompt templates for AI-generated unit tests.
Isolated from the engine for modularity and testability.
"""

TEST_GEN_SYSTEM_PYTHON = (
    "You are a senior software test engineer specializing in generating robust, runnable unit tests for Python applications. "
    "You write comprehensive pytest test suites that cover standard execution, boundary conditions, edge cases, "
    "error handling, and input validation. "
    "You ONLY output clean, runnable Python test code without conversational preamble or markdown explanations."
)

TEST_GEN_SYSTEM_JAVASCRIPT = (
    "You are a senior software test engineer specializing in generating robust, runnable unit tests for JavaScript applications. "
    "You write comprehensive test suites using modern test runner conventions (describe, it/test, expect) "
    "that cover standard execution, boundary conditions, edge cases, error handling, and input validation. "
    "You ONLY output clean, runnable JavaScript test code without conversational preamble or markdown explanations."
)


def python_test_generation_prompt(
    file_path: str,
    file_context: str,
    module_name: str,
) -> str:
    """
    Constructs a prompt to generate pytest unit tests for a specific Python file.
    """
    return f"""{TEST_GEN_SYSTEM_PYTHON}

Target Module: `{file_path}` (import name: `{module_name}`)

Structural Metadata:
{file_context}

Instructions:
1. Write a complete, standalone, runnable pytest test file for `{file_path}`.
2. Import the functions and classes from `{module_name}`.
3. Include tests for:
   - Happy path / normal behavior for each function and class method
   - Edge cases (e.g. None, empty collections, boundary numbers, 0, negative values, unexpected types)
   - Error handling and exception assertions (using pytest.raises)
   - Input validation
4. If the code uses external I/O (files, network, system calls), use `unittest.mock.patch` or pytest monkeypatch.
5. Provide ONLY runnable Python code. Ensure syntax is 100% valid Python.
"""


def javascript_test_generation_prompt(
    file_path: str,
    file_context: str,
    import_path: str,
    framework: str = "vitest",
) -> str:
    """
    Constructs a prompt to generate Vitest/Jest unit tests for a specific JavaScript file.
    """
    return f"""{TEST_GEN_SYSTEM_JAVASCRIPT}

Target Module: `{file_path}` (relative import path: `{import_path}`)
Target Framework: `{framework}`

Structural Metadata:
{file_context}

Instructions:
1. Write a complete, standalone, runnable {framework} test file for `{file_path}`.
2. Import symbols from `{import_path}` using ESM or CommonJS appropriate to the project style.
3. Use describe() blocks for each class or function group, and it() / test() blocks for individual tests.
4. Include tests for:
   - Happy path / standard execution
   - Edge cases (null, undefined, empty arrays, edge numbers)
   - Error throwing / rejection handling
   - Input validation
5. Provide ONLY runnable JavaScript/TypeScript test code.
"""
