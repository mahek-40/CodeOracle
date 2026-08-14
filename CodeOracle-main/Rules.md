# CodeOracle — Rules

## AI
- Gemini is the initial provider.
- Keep provider calls behind one small abstraction.
- No OpenAI/Ollama initially.
- Never hard-code keys.
- Handle quota/rate-limit failures clearly.
- Minimize model calls.

## Accuracy
- Never invent behavior.
- Separate observed facts from inference.
- State uncertainty.
- Preserve file/line references where possible.
- Static analysis provides facts; AI interprets them.

## Context
- Never blindly send the whole repository to Gemini.
- Use hierarchical, dependency-aware context.
- Keep prompts bounded.
- Do not remove context that changes code meaning.

## Languages
- Python mandatory; JavaScript initial second language.
- Unsupported languages must be reported honestly.
- New languages must be implemented through the adapter interface, not scattered conditionals.

## Testing
- Generated tests must be runnable.
- Coverage must come from actual execution.
- Never fabricate coverage.
- Never delete existing tests to improve coverage.
- Prefer behavior-focused tests and meaningful edge cases.
- Python: pytest + coverage.py.
- JavaScript: compatible project runner/coverage tooling.
- Use bounded retries to improve coverage toward >60%.

## Execution Safety
Uploaded code is untrusted. Never run it inside FastAPI.
Docker execution must use:
- strict timeout
- isolated filesystem
- restricted/no network
- resource limits where supported
- no host-secret access
- cleanup after execution
If isolation is unavailable, fail safely rather than executing unsandboxed.

## Refactoring
- Refactoring is always a proposal.
- Preserve behavior as the primary goal.
- Never silently overwrite original source.
- Show diffs.
- Flag public API, signature, import/export, configuration, dependency and likely behavior changes.
- Never claim semantic equivalence without evidence.
- Prefer small, reviewable changes.

## Errors
Give stage-specific errors for invalid/unsafe ZIP, inaccessible GitHub repo, unsupported language, line limit, parser failure, Gemini failure/quota, test failure, Docker failure, timeout and low coverage. Preserve earlier results when later stages fail.

## Dependencies
Prefer mature free/open-source libraries. Do not add Redis, Celery, a database, Ollama, or extra cloud services unless genuinely required.

## Scope
Do not add authentication, profiles, persistent history, private GitHub support or unrelated features before core hackathon requirements work.

## Engineering
Use TypeScript, Python type hints, clear modules, environment configuration, no secrets in Git, and run relevant build/tests after significant changes.

## Deployment
Target Render. Do not design around Vercel serverless limitations.

## Agent Behavior
Inspect existing code before architectural changes. Do not rewrite working modules unnecessarily. Update Memory.md after every phase. Record blockers instead of inventing solutions.
