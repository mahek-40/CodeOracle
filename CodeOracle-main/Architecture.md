# CodeOracle — Architecture

## Final Stack
- Frontend: React + Vite + TypeScript + Tailwind CSS
- Editor: Monaco Editor
- Graph: React Flow
- Backend: Python + FastAPI + Pydantic
- AI: Gemini API
- Python analysis: built-in `ast`
- JavaScript analysis: Tree-sitter / suitable parser
- Graph model: NetworkX or normalized graph data
- Python testing: pytest + coverage.py
- JavaScript testing: project-compatible Vitest/Jest where appropriate
- Execution: Docker sandbox
- Deployment: Render
- Storage: temporary filesystem only
- Database/auth: none

## System Flow
Browser → React → FastAPI → ingestion → language adapter → static analysis → graph → Gemini → test generation → Docker runner → coverage → refactoring → result aggregator → UI.

## Processing Pipeline
1. Create temporary job.
2. Safely download/extract source.
3. Validate files and 10,000-line limit.
4. Detect languages.
5. Run language adapters.
6. Build normalized dependency graph.
7. Build hierarchical AI context.
8. Generate explanations.
9. Generate tests.
10. Execute tests in Docker.
11. Measure coverage.
12. Generate targeted additional tests if below target, with bounded retries.
13. Generate refactor proposal.
14. Compare original/proposed code.
15. Generate breaking-change warnings.
16. Return results.
17. Clean temporary data.

## Language Adapter Contract
All languages implement the same conceptual interface:
- `detect(files)`
- `parse(file)`
- `extract_symbols(file)`
- `extract_dependencies(file)`
- `build_context(file)`
- `test_framework(project)`

Initial adapters: Python, JavaScript.
Future adapters: Java, C++, C#, Go, etc.

## Repository Structure
```text
codeoracle/
├── frontend/src/{components,pages,hooks,services,types}
├── backend/app/
│   ├── api/
│   ├── core/
│   ├── jobs/
│   ├── ingestion/
│   ├── analyzers/{base,python,javascript}
│   ├── graph/
│   ├── ai/
│   ├── tests/
│   ├── runners/
│   └── refactor/
├── benchmark/
├── Dockerfile
├── PRD.md
├── Architecture.md
├── Rules.md
├── Phases.md
├── Design.md
├── Memory.md
└── README.md
```

## API
- `POST /api/projects/upload`
- `POST /api/projects/github`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/results`
- `GET /api/jobs/{job_id}/graph`
- `GET /api/jobs/{job_id}/tests`
- `GET /api/jobs/{job_id}/refactor`
- `DELETE /api/jobs/{job_id}`

Use polling initially; do not add WebSockets unless necessary.

## AI Context
Never send a 10,000-line repository as one prompt. Use repository → module → symbol/function hierarchy plus dependency-aware context and targeted uncovered-line context.

## Docker Runner
Run uploaded/generated code only inside a temporary isolated container with timeout, restricted network, resource limits where supported, isolated filesystem, no host-secret access, and cleanup afterward. Never execute arbitrary code directly in FastAPI.

## Render
Target a single Render deployment architecture. Keep job processing simple initially; use FastAPI background processing and temporary job state. Avoid Redis/Celery unless an actual deployment limitation requires them.

## Security
Validate GitHub URLs, prevent ZIP traversal, sanitize paths, enforce archive/line limits, keep Gemini keys server-side, and never execute untrusted code outside Docker.
