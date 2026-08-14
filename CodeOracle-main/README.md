# CodeOracle — AI-Powered Legacy Codebase Intelligence & Modernization

> **Understand, test, and safely modernize any legacy Python or JavaScript codebase in minutes.**

CodeOracle combines static AST analysis, interactive dependency graphs, Gemini AI explanations, isolated Docker sandbox test generation with real line coverage measurement (>60% benchmark requirement), and backward-compatible modernization refactoring with breaking-change detection.

---

## 🌟 Key Technical Pillars

1. **Hierarchical Explanation Engine**:
   - Synthesizes repository-level architecture, module purpose, and per-symbol semantics.
   - Strictly token-bounded (<3,000 chars per module context block), line-referenced, and uncertainty-flagged.
2. **Interactive Dependency Graph**:
   - Built with React Flow with topological layout.
   - Filter by language (`Python` / `JavaScript`), search modules, and click to highlight upstream dependencies (Sky Blue) and downstream callers (Amber).
3. **Automated Test Generation & Real Docker Coverage**:
   - Writes executable `pytest` and `vitest` unit test suites.
   - Executes inside an isolated Docker sandbox with resource limits (`--network none`, `--memory 512m`, `--cpus 1.0`, `--pids-limit 100`, 30s timeout).
   - Measures genuine statement line coverage with `coverage.py` and Istanbul. Iterative feedback loop achieves >60% line coverage on benchmarks.
4. **AI Refactoring & AST Breaking Change Detection**:
   - Modernizes legacy code non-destructively into `{job_dir}/refactored/` (**original files are never overwritten**).
   - AST symbol comparator detects parameter changes, removed public methods, return-type alterations, and escalates severity to Critical when cross-module callers exist.
   - Non-regression test validator executes test suites against refactored code.
5. **Zero-Database Client-Side Exports**:
   - One-click downloads for Explanation Reports (`.md`), Dependency Graphs (`.json`), Coverage Reports (`.json`), Refactoring Unified Diff Patches (`.patch`), and Full Project Audits (`.json`).

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│             CodeOracle Web Dashboard (React + TS)     │
│  - Landing & 1-Click Judge Presets                     │
│  - React Flow Dependency Graph                         │
│  - Gemini Explanation Inspector                        │
│  - Test Suite & Coverage Progress Gauge                │
│  - Side-by-Side Split Diff & Breaking Warnings Panel   │
└───────────────────────────┬────────────────────────────┘
                            │ REST API (JSON)
┌───────────────────────────▼────────────────────────────┐
│               FastAPI Intelligence Backend             │
│  - Secure Ingestion (Zip Slip & Path Traversal Guards) │
│  - AST Adapters (Python ast, JS regex-AST)             │
│  - Dependency Graph Builder                            │
│  - GeminiProvider (google-genai SDK, Retries/Quota)    │
│  - CoverageEngine (Iterative Bounded Feedback Loop)    │
│  - RefactoringEngine & AST Breaking Change Detector    │
└───────────────────────────┬────────────────────────────┘
                            │ Docker CLI / API
┌───────────────────────────▼────────────────────────────┐
│            Isolated Docker Execution Sandbox           │
│  - python:3.11-slim / node:20-slim                     │
│  - --network none, 512MB RAM, 1.0 CPU, 30s Timeout     │
│  - Real pytest, coverage.py, Vitest execution          │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Configure Gemini API Key (Optional for static graph & ingestion, required for AI):
set GEMINI_API_KEY="your-api-key-here"  # Windows cmd
$env:GEMINI_API_KEY="your-api-key-here" # PowerShell
export GEMINI_API_KEY="your-api-key-here" # Linux/macOS

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** to access the CodeOracle dashboard.

---

## 🧪 Running Automated Tests

### Backend Test Suite (93 unit & integration tests)
```bash
python -m pytest backend/app/tests -v
```

### Frontend Production Build Verification
```bash
cd frontend
npm run build
```

---

## 🔒 Security Guarantees

- **Zip Slip & Path Traversal Protection**: Archive members are verified against destination roots with multi-separator normalization.
- **Untrusted Code Execution Sandbox**: Uploaded code is **never** executed inside FastAPI. Execution occurs exclusively in resource-constrained Docker containers with `--network none`.
- **Non-Destructive Storage**: Original source files are stored immutably. Refactored code is generated into isolated subdirectories.
- **Secret Isolation**: `GEMINI_API_KEY` is read strictly on the server; zero secrets or tokens are ever exposed to the client.

---

## 🚢 Render Deployment

CodeOracle includes a pre-configured [render.yaml](file:///e:/CodeOracle-main/CodeOracle-main/render.yaml) blueprint:

1. **Backend Web Service**: Docker environment built from root [Dockerfile](file:///e:/CodeOracle-main/CodeOracle-main/Dockerfile) exposing port `8000` with health check on `/api/health`.
2. **Frontend Static Site**: Static build running `cd frontend && npm install && npm run build` serving from `./frontend/dist`.
3. Set environment variable `GEMINI_API_KEY` in the Render dashboard for the `codeoracle-backend` service.

---

## ⚖️ License
MIT License © 2026 CodeOracle Team. Built for the Gemini AI Developer Competition.
