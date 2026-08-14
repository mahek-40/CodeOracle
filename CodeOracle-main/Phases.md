# CodeOracle — Implementation Phases

## Phase 0 — Foundation
React/Vite/TypeScript frontend, FastAPI backend, monorepo, env config, health endpoint, Render config.
**Exit:** frontend and backend communicate.

## Phase 1 — Ingestion
ZIP upload, public GitHub URL, safe extraction, ignore rules, language detection, 10k-line validation, temporary jobs.
**Exit:** real projects can be accepted.

## Phase 2 — Language Adapters
Common adapter interface; Python `ast`; JavaScript Tree-sitter/parser; symbols/imports/dependencies; normalized schema.
**Exit:** both languages produce normalized analysis.

## Phase 3 — Dependency Graph
Graph construction, API, React Flow UI, search/filter, node details.
**Exit:** project structure is visually understandable.

## Phase 4 — AI Explanation
Gemini abstraction, structured prompts, repository/module/function explanations, source references, uncertainty.
**Exit:** judge-ready explanation quality.

## Phase 5 — Test Generation
Generate tests, respect existing frameworks, write to temporary workspace, Docker runner, execute and capture results.
**Exit:** generated tests actually execute in isolation.

## Phase 6 — Coverage
coverage.py for Python and suitable JS coverage; actual coverage; identify uncovered areas; targeted additional tests; bounded retries.
**Exit:** >60% benchmark line coverage where feasible.

## Phase 7 — Refactoring
Modernization detection, proposed code, diffs, API/signature/import/export checks, breaking-change warnings, optional refactor test execution.
**Exit:** safe, reviewable refactor output.

## Phase 8 — Results UI
Four required tabs, project summary, languages, line count, status, coverage, warnings, downloads, error/retry states.
**Exit:** complete judge workflow.

## Phase 9 — Benchmark & Hardening
Python/JS benchmarks, 10k-line project, malformed/unsafe ZIP, inaccessible repo, unsupported language, parser/AI errors, timeout, Docker failure, low coverage.
**Exit:** expected failures are handled.

## Phase 10 — Deployment
Render deployment, Gemini secret, origins, Docker verification, temporary storage, full deployed workflow and benchmark.
**Exit:** public deployment works end-to-end.

## Priority If Time Is Limited
1. Ingestion
2. Python analysis
3. Gemini explanation
4. Real test generation/execution/coverage
5. Dependency graph
6. Refactoring + warnings
7. JavaScript quality
8. Visual polish
