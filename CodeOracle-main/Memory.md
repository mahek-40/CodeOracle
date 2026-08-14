# CodeOracle — AI Coding Memory

This file is the coding agent's source of truth. Update it after every completed phase.

## Current Status
- Phase: Phase 5/6 Critical Fix — Real Test Execution & Coverage Pipeline Overhaul — Completed
- Overall status: System fully audited, repaired, and hardened (104/104 backend tests passing, 0% coverage fabrication eliminated, multi-manifest dependency installer active, test quality validator active, multi-format coverage parsers verified on arbitrary repositories)
- Last updated: Real Test Execution & Coverage Pipeline completion

## Completed
- Final product scope defined.
- Final architecture defined.
- Final engineering rules defined.
- Final implementation phases defined.
- Final design system defined.
- **Accuracy & Reliability Audit & Repair Pass Implemented**:
  - Ingestion: Added `_flatten_single_subdir` to `ZipHandler` to prevent path nesting issues in single-folder ZIP uploads.
  - JavaScript Adapter: Overhauled with brace-balanced AST scanning for exact line ranges (eliminated hardcoded `idx + 5`), full class method parsing (including constructor, static, async, getters/setters), parameter types and default values.
  - Python Adapter: Added `level` tracking for relative imports and extracted parameter default values for accurate signature diffing.
  - Dependency Graph: Overhauled `_resolve_import` with `os.path.normpath` (eliminated destructive `lstrip` breaking `../`), added candidate checks for `/index.js`, `/index.ts`, `/__init__.py`, dot-relative imports, and root aliases.
  - Context & Explanations: Enriched context builder with class method signatures and parameter defaults; enforced line-grounding rules in prompts.
  - Test Generation & Coverage: Corrected generated JavaScript test relative import paths (`../{fa.path}` from `generated_tests/`) and validated syntax prior to disk save.
  - Breaking Change Detection: Differentiated required positional parameter additions (breaking) from optional parameter additions with default values (non-breaking) to prevent false-positive critical warnings.
  - Multi-Language Benchmarks: Created `benchmark/mixed_project/` containing dual-language inter-connected modules and `test_accuracy_audit.py` test suite (98/98 tests passing).
- **Phase 5/6 Critical Fix — Real Test Execution & Coverage Pipeline Overhauled**:
  - Root Causes Identified: (1) Missing pre-execution dependency installer causing `ModuleNotFoundError` during test collection, (2) Lack of test quality validator allowing trivial assertions / placeholders, (3) Docker daemon unavailability silently falling back to a fabricated 0% coverage report, (4) Incomplete parser coverage for XML/LCOV formats, (5) Silent fake 0% fallback in `CoverageEngine`.
  - Multi-Manifest Dependency Installer (`backend/app/runners/dependency_manager.py`): Automatically discovers and installs Python (`requirements.txt`, `pyproject.toml`, `setup.py`) and JavaScript (`package.json`) dependencies before test execution. Halts execution cleanly with `status="dependency_install_failed"`, `stage="dependency_installation"`, and exact logs if dependencies fail to resolve.
  - Test Quality Validator (`backend/app/runners/test_validator.py`): Inspects generated test code before saving to disk; rejects empty test suites, TODO/placeholder comments, trivial assertions (`assert True`, `expect(true).toBe(true)`), and syntax errors. Integrated into `TestGenerator` with targeted retries.
  - Execution Sandbox & Subprocess Fallback (`backend/app/runners/docker_runner.py`): Added fallback subprocess runner with `PYTHONPATH` injection when Docker is unavailable. Captures `install_logs`, `execution_logs`, and accurately measures test results and coverage without silent failures.
  - Zero-Fabrication Multi-Format Coverage Parsers (`backend/app/coverage/parser.py`): Full support for Python JSON (`coverage.json`), Python XML Cobertura (`coverage.xml`), JavaScript JSON (`coverage-summary.json`, `coverage-final.json`), and JavaScript LCOV (`lcov.info`).
  - Strict Integrity in `CoverageEngine` (`backend/app/coverage/engine.py`): Completely eliminated fake 0% coverage reports; returns structured `status="failed"`, exact failure stage, and error details when test execution fails.
  - Frontend Diagnostics UI (`frontend/src/components/CoverageDashboard.tsx`, `GeneratedTestsView.tsx`): Displays explicit failure state banners with stage badges, exact error reasons, and dedicated "Dependency Logs" and terminal stdout/stderr tabs.
  - Integration Test Suite (`backend/app/tests/test_coverage_pipeline.py`): 6 comprehensive integration tests (104/104 backend tests passing across the repository).
- **Phase 0 Foundation Implemented**: React+Vite+TS frontend, FastAPI backend, health endpoint, Render config.
- **Phase 1 Project Ingestion Implemented**: ZIP upload (with Zip Slip protection), public GitHub download, file scanning, 10,000 line limit, job workspace management.
- **Phase 2 Language Adapters Implemented**: `LanguageAdapter` abstract contract, `PythonAdapter` (ast), `JavaScriptAdapter` (regex-AST), `AdapterRegistry`, normalized `ProjectAnalysis` schema, integrated into API pipeline.
- **Phase 3 Dependency Graph Implemented**:
  - `GraphNode`/`GraphEdge`/`DependencyGraph` schema in `backend/app/graph/schema.py`.
  - `GraphBuilder` in `backend/app/graph/builder.py`.
  - `GET /api/jobs/{job_id}/graph` endpoint.
  - `reactflow` added to frontend.
  - `DependencyGraph` React component in `frontend/src/components/DependencyGraph.tsx`.
- **Phase 4 Gemini Explanation Engine Implemented**:
  - `GeminiProvider` abstraction layer (`backend/app/ai/provider.py`): Lazy client initialization using `google-genai` SDK, API key read exclusively from server environment (`GEMINI_API_KEY`), handles `AIKeyMissingError`, `AIQuotaError`, `AITimeoutError`, `AIResponseError`, `AIServiceError` with retry logic for 429/500/503.
  - `ExplanationEngine` & `ContextBuilder` (`backend/app/ai/engine.py`, `backend/app/ai/context_builder.py`): Hierarchical context construction (repo overview -> per-file -> per-symbol), bounded prompts (<3,000 chars per file context block, never sends raw source code or entire 10k-line repo at once), structured prompt templates with line references and explicit uncertainty instructions.
  - Explanation Schema (`backend/app/ai/schema.py`): `ProjectExplanation`, `FileExplanation`, `SymbolExplanation`.
  - `GET /api/jobs/{job_id}/explain` API endpoint returning structured project explanations and handling all AI error codes (503 missing key, 429 quota, 504 timeout, 502 service error).
  - Test Suite (`backend/app/tests/test_explain.py`): 24 tests covering context builder bounds, prompt generation, mocked provider behavior, entry point heuristics, partial failure handling, and API status codes.
  - Frontend UI (`frontend/src/components/ExplanationView.tsx`): Integrated under Explanation tab, features custom markdown-like Gemini renderer, expandable file cards, symbol accordions, entry points list, partial warning banner, and error handling states.
- **Phase 5 AI Test Generation & Isolated Docker Execution Implemented**:
  - `TestPrompts` (`backend/app/ai/test_prompts.py`): Dedicated structured prompt templates for Python (`pytest`) and JavaScript (`vitest`).
  - `TestGenerator` (`backend/app/runners/test_generator.py`): AST + Graph-aware test generator, code-block extraction, Python `ast.parse` syntax verification, test count estimation, and disk storage in `{job_dir}/generated_tests/`.
  - `DockerRunner` (`backend/app/runners/docker_runner.py`): Sandboxed execution container enforcing `--network none`, `--memory 512m`, `--cpus 1.0`, `--pids-limit 100`, 30s timeout, safe fail-safe when Docker is unavailable (`DockerUnavailableError`).
  - `OutputParser` (`backend/app/runners/output_parser.py`): Parses pytest and Vitest/Jest stdout/stderr into structured test counts, status, and test case items.
  - Test API Endpoints (`backend/app/api/tests.py`): `POST /api/jobs/{id}/tests/generate`, `POST /api/jobs/{id}/tests/run`, `GET /api/jobs/{id}/tests`.
  - Test Suite (`backend/app/tests/test_test_generation.py`, `test_docker_runner.py`, `test_tests_api.py`): 20 new tests (64 total across backend) covering generation, sandboxing, parsing, and API error codes.
  - Frontend UI (`frontend/src/components/GeneratedTestsView.tsx`): Generated Tests dashboard tab with Generate/Run buttons, file browser, syntax code viewer, stdout/stderr tabbed console, test cases summary, and Phase 6 coverage placeholder.
- **Phase 6 Real Coverage Measurement & Targeted Test Retries Implemented**:
  - `CoverageSchema` (`backend/app/coverage/schema.py`): Normalized `FileCoverage`, `CoverageReport`, `CoverageIteration`, and `CoverageImprovementResult` models.
  - `CoverageParser` (`backend/app/coverage/parser.py`): Parses real `coverage.py` JSON and Vitest/Istanbul reports while filtering out test and framework internals.
  - `TargetedContextBuilder` (`backend/app/coverage/targeted_builder.py`): Intersects missing line numbers with AST functions/classes to build token-bounded prompts with only uncovered functions and branches.
  - `CoveragePrompts` (`backend/app/ai/coverage_prompts.py`): Focused prompt templates instructing Gemini to write tests exclusively for uncovered statements.
  - `CoverageEngine` (`backend/app/coverage/engine.py`): Orchestrates iterative coverage feedback loop with bounded retries (max 3 retries), measuring real Docker container coverage and stopping once >=60% target coverage is reached.
  - Coverage API Endpoints (`backend/app/api/coverage.py`): `POST /api/jobs/{id}/coverage/run`, `POST /api/jobs/{id}/coverage/improve`, `GET /api/jobs/{id}/coverage`.
  - Benchmark Projects (`benchmark/python_project/`, `benchmark/javascript_project/`): Multi-module realistic benchmark suites.
  - Frontend UI (`frontend/src/components/CoverageDashboard.tsx`, `GeneratedTestsView.tsx`): Real-time coverage progress gauge, 60% benchmark badge, per-file line breakdown table, uncovered lines inspector, and iteration timeline.
  - Test Suite (`backend/app/tests/test_coverage_parser.py`, `test_targeted_builder.py`, `test_coverage_engine.py`, `test_coverage_api.py`): 13 new unit/integration tests (77 total backend tests passing).
- **Phase 7 AI Refactoring & Modernization Engine Implemented**:
  - `RefactorSchema` (`backend/app/refactor/schema.py`): Normalized models for `DiffLine`, `FileDiff`, `ModernizationOpportunity`, `BreakingChangeWarning`, `RefactoredFile`, `RiskSummary`, `ValidationComparison`, `RefactorResult`.
  - `RefactorPrompts` (`backend/app/ai/refactor_prompts.py`): Structured prompts instructing Gemini on f-strings, type annotations, context managers, modern exception handling, ES modules, const/let, async/await, optional chaining, and public interface preservation.
  - `DiffEngine` (`backend/app/refactor/diff_engine.py`): Line-by-line structured additions, deletions, modifications, and unified diff output using `difflib`.
  - `BreakingChangeDetector` (`backend/app/refactor/breaking_detector.py`): AST symbol diffing checking function/method signatures, parameter additions/removals/renamings, return type annotations, classes, and escalating severity using the `DependencyGraph`.
  - `RefactorValidator` (`backend/app/refactor/validator.py`): Isolated Docker sandbox runner executing test suites against refactored code to measure non-regression equivalence, pass rates, and coverage deltas.
  - `RefactoringEngine` (`backend/app/refactor/engine.py`): Non-destructive refactoring coordinator generating proposed code into `{job_dir}/refactored/` without ever touching original source files.
  - Refactor API Endpoints (`backend/app/api/refactor.py`): `POST /api/jobs/{id}/refactor/generate`, `GET /api/jobs/{id}/refactor`, `GET /api/jobs/{id}/refactor/warnings`, `GET /api/jobs/{id}/refactor/diffs`, `POST /api/jobs/{id}/refactor/validate`, `GET /api/jobs/{id}/refactor/validate`.
  - Frontend UI (`frontend/src/components/RefactoredCodeView.tsx`): Split-pane diff viewer, unified diff view, breaking change warnings panel with severity filters, modernization opportunities insights, risk score summary, and test validation panel.
  - Test Suite (`backend/app/tests/test_refactor_schema.py`, `test_diff_engine.py`, `test_breaking_detector.py`, `test_refactor_engine.py`, `test_refactor_api.py`): 11 new tests (88 total backend tests passing).
- **Phase 8 Complete User Experience & Results Interface Implemented**:
  - `ExportUtilities` (`frontend/src/utils/export.ts`): Client-side direct blob downloads for Explanation Markdown (`.md`), Dependency Graph (`.json`), Coverage Report (`.json`), Refactoring Unified Diff (`.patch`), and Full Project Audit (`.json`) with zero server database requirements.
  - `EnhancedLandingView` (`frontend/src/App.tsx`): Drag-and-drop ZIP upload with validation badges, public GitHub URL clone input, and 1-Click Judge Quick-Start presets for Python and JavaScript multi-module benchmarks.
  - `RealTimeProcessingView` (`frontend/src/App.tsx`): 7-stage live pipeline screen tracking Ingestion, AST Analysis, Dependency Graph, Explanation, Test Generation, Coverage Analysis, and AI Refactoring with live duration timer.
  - `EnhancedDependencyGraph` (`frontend/src/components/DependencyGraph.tsx`): MiniMap, language filters, search input, node click highlighting for upstream dependencies (Sky Blue) and downstream callers (Amber), and node details drawer.
  - `EnhancedExplanationView` (`frontend/src/components/ExplanationView.tsx`): Search filter across files & symbols, copy button for code identifiers, expand/collapse toggles, and Markdown report export.
  - `ExportDropdownMenu` (`frontend/src/App.tsx`): Direct 1-click header dropdown to export all analysis artifacts.
  - Test Suite (`backend/app/tests/test_export_formats.py`): 3 new tests (91 total backend tests passing).
- **Phase 9 Final Hardening, Security, Performance & Deployment Readiness Implemented**:
  - Security Review & Hardening: Validated Zip Slip path traversal checks (`zip_handler.py`), resource limits and timeout enforcement (`docker_runner.py`), environment secret isolation (`provider.py`), and error message sanitization.
  - Performance & Stress Testing: Validated 10,000-line codebase handling (`test_benchmark_performance.py` passing in 0.27s).
  - Render Deployment Configuration: Hardened `render.yaml`, `Dockerfile` (dynamic PORT handling), and updated `backend/requirements.txt`.
  - Comprehensive Documentation: Updated [README.md](file:///e:/CodeOracle-main/CodeOracle-main/README.md), created [DEMO_GUIDE.md](file:///e:/CodeOracle-main/CodeOracle-main/DEMO_GUIDE.md) (3-minute judge script), and [DEPLOYMENT.md](file:///e:/CodeOracle-main/CodeOracle-main/DEPLOYMENT.md).
  - Test Suite (`backend/app/tests/test_benchmark_performance.py`): 2 new tests (93 total backend tests passing).

## In Progress
- None (Phase 9 completed, ready for Phase 10).

## Next Task
Phase 10 — Render Production Deployment:
1. Verify remote GitHub repository synchronization.
2. Confirm live Render service health checks and environment variable setup.
3. Perform live sanity check against deployed frontend and backend.

## Final Technology Decisions
- React + Vite + TypeScript + Tailwind + reactflow + jszip
- FastAPI + Python
- Gemini API (`google-genai` SDK)
- Python built-in `ast`; JavaScript regex-AST
- pytest + coverage.py
- Docker sandbox (Phase 5+)
- Render
- Temporary filesystem; no database; no authentication

## Architecture Decisions
- Gemini access is hidden behind `GeminiProvider` abstraction.
- API key is never exposed to the frontend.
- AI engine never receives raw source code or unbounded repo context — receives structured summaries built by `ContextBuilder`.
- Individual file explanation failures do not fail the whole request; partial explanations are returned and flagged.
- Coverage is never simulated, estimated, or fabricated — measured directly from `coverage.py` or Vitest execution in Docker.
- Targeted retry loop is strictly bounded to MAX_COVERAGE_RETRIES (3) to prevent infinite loops and runaway costs.
- Original source files are NEVER overwritten during refactoring; proposed code is stored in `{job_dir}/refactored/`.
- Refactorings are never claimed to be guaranteed safe; warnings carry structured severity tiers and mitigation advice.
- All export operations are client-side blob downloads; no persistent database or user accounts required.

## Known Issues
None.

## Environment Variables
Never store secret values here. `GEMINI_API_KEY` is read from server environment only.

## Verification Checklist
- [x] Frontend runs
- [x] Backend runs
- [x] Frontend reaches backend
- [x] ZIP upload works
- [x] Public GitHub ingestion works
- [x] Python adapter works
- [x] JavaScript adapter works
- [x] Dependency graph works
- [x] Gemini explanation engine works
- [x] Generated tests work
- [x] Docker runner works
- [x] Real coverage works
- [x] >60% benchmark coverage achieved
- [x] Refactoring works
- [x] Breaking-change warnings work
- [x] 10k-line project handled
- [ ] Render deployment works

## Agent Update Rule
After each phase:
- Update Current Status.
- Move finished work into Completed.
- Record important decisions.
- Record bugs/blockers.
- Update verification checkboxes.
- Set the next smallest concrete task.
