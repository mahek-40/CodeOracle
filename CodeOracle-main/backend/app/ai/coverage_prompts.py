"""
Targeted coverage prompts — focused prompts that send ONLY uncovered functions
and missing line ranges to Gemini to maximize token efficiency and drive coverage >60%.
"""

TARGETED_SYSTEM_PYTHON = (
    "You are a test optimization specialist. Your goal is to write targeted pytest tests "
    "specifically designed to execute currently UNCOVERED code branches, edge cases, and error handlers. "
    "You ONLY output clean, runnable Python test code without markdown explanations."
)

TARGETED_SYSTEM_JAVASCRIPT = (
    "You are a test optimization specialist. Your goal is to write targeted Vitest/Jest tests "
    "specifically designed to execute currently UNCOVERED code branches, edge cases, and error handlers. "
    "You ONLY output clean, runnable JavaScript test code without markdown explanations."
)


def targeted_python_coverage_prompt(
    file_path: str,
    module_name: str,
    uncovered_context: str,
) -> str:
    """
    Constructs a prompt focused strictly on uncovered areas of a Python file.
    """
    return f"""{TARGETED_SYSTEM_PYTHON}

Target Module: `{file_path}` (import name: `{module_name}`)

Uncovered Areas & Target Functions:
{uncovered_context}

Instructions:
1. Write specific additional pytest tests targeting ONLY the uncovered functions, missing line ranges, and unexercised branches listed above.
2. Import `{module_name}` and invoke the uncovered functions with inputs that trigger:
   - Branch conditions (if/elif/else paths)
   - Exception handlers and error conditions
   - Edge case arguments (empty, None, boundary numbers, invalid types)
3. Ensure all tests are runnable and have proper assertions.
4. Output ONLY valid, runnable Python code.
"""


def targeted_javascript_coverage_prompt(
    file_path: str,
    import_path: str,
    uncovered_context: str,
    framework: str = "vitest",
) -> str:
    """
    Constructs a prompt focused strictly on uncovered areas of a JavaScript file.
    """
    return f"""{TARGETED_SYSTEM_JAVASCRIPT}

Target Module: `{file_path}` (import path: `{import_path}`)
Framework: `{framework}`

Uncovered Areas & Target Functions:
{uncovered_context}

Instructions:
1. Write specific additional {framework} tests targeting ONLY the uncovered functions and missing branches listed above.
2. Import from `{import_path}` and invoke the uncovered functions with inputs that trigger:
   - Untested conditional branches
   - Thrown errors and promise rejections
   - Boundary values and edge cases
3. Output ONLY valid, runnable JavaScript/TypeScript code.
"""
