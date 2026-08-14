# CodeOracle — Product Requirements Document

## Product
CodeOracle is an AI-powered developer tool that analyzes legacy codebases and helps developers understand, test, and modernize them safely.

## Hackathon Requirements
Accept a ZIP or public GitHub repository and generate:
1. Natural-language explanations at module and function level.
2. An interactive dependency graph.
3. Automatically generated runnable unit tests.
4. A proposed modern refactor with breaking-change warnings.

## MVP Scope
- Python mandatory.
- JavaScript initial second language.
- Maximum 10,000 source lines.
- ZIP upload and public GitHub URL.
- Results tabs: Explanation, Dependency Graph, Generated Tests, Refactored Code.
- Real test execution and real line coverage.
- Target >60% line coverage on benchmark scripts.
- Architecture uses pluggable language adapters so Java/C++/etc. can be added later.
- No login, user profiles, persistent history, or database.

## User Flow
Upload ZIP / enter public GitHub URL → validate/extract → detect languages → static analysis → dependency graph → Gemini explanations → Gemini tests → isolated Docker execution → coverage → targeted extra tests if needed → Gemini refactor → diff + breaking-change warnings → results.

## Functional Requirements
### Ingestion
- Validate ZIP and prevent path traversal.
- Support public GitHub repositories only.
- Ignore `.git`, `node_modules`, virtual environments, caches and build artifacts.
- Enforce 10,000 source-line limit.

### Analysis
Python uses built-in `ast`.
JavaScript uses Tree-sitter or an appropriate parser.
Extract files, modules, imports, classes, functions, calls and dependencies.

### Explanation
Provide repository, module and function/class explanations; inputs/outputs, side effects, dependencies and edge cases when inferable. Preserve file/line references where possible and state uncertainty.

### Tests
Use pytest + coverage.py for Python. For JavaScript, respect an existing test framework or use a supported runner such as Vitest/Jest. Tests must actually execute and coverage must never be fabricated.

### Refactoring
Show original vs proposed code and diffs. Detect likely changes to APIs, signatures, imports/exports, configuration, dependencies and behavior. Never silently replace original code or claim semantic equivalence without evidence.

## Non-Functional
- Handle up to 10,000 lines.
- Long work runs as jobs, not blocking HTTP requests.
- Uploaded/generated code is executed only in isolated Docker.
- Temporary storage only.
- Secrets stay server-side.

## AI/Cost
- Gemini API initially.
- No OpenAI or Ollama dependency initially.
- Keep a small provider abstraction for future providers.
- Minimize API calls using static analysis and hierarchical context.
- Design for free/available quota; never assume unlimited usage.

## Deployment
Deploy on Render. Keep infrastructure simple and avoid extra cloud services.

## Success Criteria
A judge can upload a real project and complete the full workflow: useful explanations, graph, runnable generated tests, measured >60% benchmark coverage where feasible, refactor proposal, and breaking-change warnings.

## Out of Scope
Authentication, private GitHub repos, persistent accounts/history, production deployment of refactored code, guaranteed semantic equivalence, and full language coverage.
