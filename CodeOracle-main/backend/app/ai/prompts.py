"""
Explanation prompts — isolated from the engine so prompts can be tested independently.
"""

REPO_OVERVIEW_SYSTEM = (
    "You are a senior software engineer specializing in reading and explaining legacy codebases. "
    "You are precise, cite specific files and line numbers when you have them, "
    "and state 'uncertain' explicitly when evidence is insufficient. "
    "You never invent facts. Respond in clear technical prose."
)


def repo_overview_prompt(repo_context: str) -> str:
    return f"""{REPO_OVERVIEW_SYSTEM}

Analyze the following project metadata derived from static analysis. Do NOT assume you have seen the actual source code — only use the structural information provided below.

{repo_context}

Provide a structured overview covering:
1. **Purpose**: What does this project likely do based on its structure, file names, and symbols?
2. **Architecture**: How is the code organized? Note any layering, separation of concerns, or patterns visible from the structure.
3. **Entry points**: Which files are most likely the main entry points? Explain why.
4. **Key dependencies** (within-project): Which files are most heavily depended upon by other files?
5. **Languages and tech stack**: What languages and frameworks can be inferred?
6. **Uncertainty**: Clearly list anything you cannot determine from static analysis alone.

Be specific. Reference file paths and line ranges wherever the data supports it. Keep the response under 600 words."""


def file_explanation_prompt(file_context: str) -> str:
    return f"""{REPO_OVERVIEW_SYSTEM}

Explain the following file based solely on its static analysis metadata (no raw source code is provided).

{file_context}

Provide:
1. **Purpose**: What is this file/module responsible for?
2. **Key exports**: What does it expose to the rest of the project?
3. **Dependencies**: What does it import or rely on?
4. **Notable patterns**: Any design patterns, error handling strategies, or architectural decisions visible from the structure?
5. **Uncertainty**: What cannot be determined without seeing the implementation body?

Reference specific line numbers for classes and functions where the data provides them. Keep under 400 words."""


def symbol_explanation_prompt(symbol_context: str, symbol_type: str) -> str:
    return f"""{REPO_OVERVIEW_SYSTEM}

Explain the following {symbol_type} based solely on its static analysis metadata.

{symbol_context}

Provide:
1. **Summary**: What does this {symbol_type} do?
2. **Inputs**: What parameters does it accept and what types/shapes are expected?
3. **Outputs/Return value**: What does it return or produce?
4. **Side effects**: Does it modify state, make I/O calls, or produce observable side effects?
5. **Edge cases**: What edge cases or failure modes can be inferred from the signature or calls?
6. **Dependencies**: What other symbols or modules does it call?
7. **Uncertainty**: What cannot be determined from the signature and docstring alone?

Keep under 300 words. Reference the file path and line numbers."""
