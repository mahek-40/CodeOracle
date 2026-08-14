"""
Refactoring prompt templates for Python and JavaScript source code.
Instructs Gemini to modernize legacy syntax, add types, improve readability and safety,
while maintaining backward compatibility for public APIs where possible.
"""

def python_refactor_prompt(
    file_path: str,
    file_summary: str,
    original_code: str,
    dependent_callers: str = "",
) -> str:
    """
    Builds a prompt requesting a modernized Python refactoring.
    """
    callers_section = ""
    if dependent_callers:
        callers_section = f"### Cross-Module Dependents (Callers that rely on this module):\n{dependent_callers}\n\n"

    prompt = f"""You are an expert Python software architect specializing in legacy codebase modernization.
Your task is to modernize and refactor the Python source file `{file_path}` to modern, idiomatic, clean Python (3.10+).

### File Summary & AST Context:
{file_summary}

{callers_section}### Modernization Guidelines:
1. **Modern Python Syntax**:
   - Replace `%` formatting and `.format()` with f-strings (`f"..."`).
   - Add clear type annotations to all function parameters and return types (using `typing` or built-in generics).
   - Use `with` statement context managers for resource management (files, locks, connections).
   - Replace manual dictionary loops or redundant indexing with list/dict comprehensions where clear.
   - Use `@dataclass` or clean classes where appropriate.
   - Upgrade exception handling with explicit exception types and proper chaining (`raise ... from err`).
2. **Readability & Structure**:
   - Remove dead code, redundant branches, or unnecessary temporary variables.
   - Improve variable/parameter naming for clarity without breaking public interfaces.
   - Add concise docstrings explaining complex logic.
3. **API Compatibility**:
   - Preserve existing public function names, class names, and parameter order so downstream callers do not break unexpectedly.
4. **Safety & Robustness**:
   - Add input validation and defensive guards against None / null values.

### Original Source Code:
```python
{original_code}
```

### CRITICAL OUTPUT FORMAT:
Return ONLY the complete, executable modernized Python source code.
Enclose the source code in a single ```python ... ``` markdown code block.
Do NOT include any introductory greetings, explanations, or commentary outside the code block.
"""
    return prompt.strip()


def javascript_refactor_prompt(
    file_path: str,
    file_summary: str,
    original_code: str,
    dependent_callers: str = "",
) -> str:
    """
    Builds a prompt requesting a modernized JavaScript refactoring.
    """
    callers_section = ""
    if dependent_callers:
        callers_section = f"### Cross-Module Dependents (Callers that rely on this module):\n{dependent_callers}\n\n"

    prompt = f"""You are an expert JavaScript software architect specializing in legacy codebase modernization.
Your task is to modernize and refactor the JavaScript source file `{file_path}` to modern, clean ES2022+ standards.

### File Summary & Context:
{file_summary}

{callers_section}### Modernization Guidelines:
1. **Modern ES Syntax**:
   - Replace all `var` declarations with `const` and `let`.
   - Use ES Modules (`import`/`export`) syntax.
   - Use arrow functions for callbacks and concise methods.
   - Use `async`/`await` instead of raw Promise chains or callbacks.
   - Use optional chaining (`obj?.prop`) and nullish coalescing (`a ?? b`).
   - Use template literals (` `) instead of string concatenation with `+`.
   - Use destructuring (`const {{ a, b }} = obj`) for cleaner parameter handling.
2. **Readability & Safety**:
   - Remove dead code and unused variables.
   - Add defensive parameter type guards and validation.
   - Use modern Array methods (`map`, `filter`, `reduce`, `find`, `some`, `every`).
3. **API Compatibility**:
   - Preserve existing exported function names, class names, and parameter order so downstream callers do not break.

### Original Source Code:
```javascript
{original_code}
```

### CRITICAL OUTPUT FORMAT:
Return ONLY the complete, executable modernized JavaScript source code.
Enclose the source code in a single ```javascript ... ``` markdown code block.
Do NOT include any introductory greetings, explanations, or commentary outside the code block.
"""
    return prompt.strip()
