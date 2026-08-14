# CodeOracle — Hackathon Judge Demo Guide

A 3-minute end-to-end evaluation walkthrough for hackathon judges.

---

## 🎯 1-Click Evaluation (Fastest Path)

1. Open the CodeOracle web application at `http://localhost:5173`.
2. In the **"Judge Quick Start: Built-In Benchmark Presets"** section on the landing screen:
   - Click **"Python Order Processing Suite"** (or **"JavaScript Cart Manager Suite"**).
3. The platform instantly generates in-memory multi-module test projects, unpacks them safely, scans ASTs, and launches the results dashboard.

---

## 🗺️ Step-by-Step Judge Walkthrough

### Step 1: Interactive Dependency Graph (Tab 1)
- **What to Observe:**
  - Full topological module hierarchy rendered via React Flow.
  - Node language pills (`PYTHON` / `JAVASCRIPT`) and line counts.
  - Click any node (e.g. `order_processor.py`) to see upstream dependencies highlighted in **Sky Blue** and downstream callers highlighted in **Amber**.
  - Review file metadata in the interactive right-side drawer.

### Step 2: Architectural Explanation Engine (Tab 2)
- **What to Observe:**
  - Click **"Generate Explanation"** to activate the Gemini explanation engine.
  - Review the repository-level overview, primary entry points (`⚡ order_processor.py`), and per-file module summaries.
  - Expand function and class accordions to inspect line-bounded explanations (`L10-25`).
  - Click **"Export Markdown"** to download a clean, formatted Markdown report.

### Step 3: Generated Tests & Real Line Coverage (Tab 3)
- **What to Observe:**
  - Click **"Generate Test Suite"** to author full unit tests with `pytest` / `vitest`.
  - Click **"Run Test Suite in Docker Sandbox"** to execute the tests in an isolated, resource-constrained container (`--network none`, 512MB RAM).
  - Review stdout/stderr terminal output and test pass/fail results.
  - Observe the **Coverage Dashboard**:
    - Real line coverage measured directly by `coverage.py` / Istanbul (never simulated).
    - Click **"Target Uncovered Lines with AI"** to run the targeted iterative improvement loop and witness real line coverage surpass the **>60% hackathon benchmark**.

### Step 4: AI Refactoring & AST Breaking-Change Warnings (Tab 4)
- **What to Observe:**
  - Click **"Generate Modern Refactor"**.
  - **Split Diff Viewer**: Review side-by-side original source vs modernized code (Python 3.10+ type annotations, f-strings, context managers / ES2022+ const/let, async/await).
  - **Breaking Change Warnings Panel**: Filter warnings by severity (Critical / High / Medium / Low). Notice how AST comparator checks method signatures, parameter names, and flags affected cross-module callers from the dependency graph.
  - **Validate against Test Suite**: Click this button to run non-regression tests inside the Docker sandbox against the proposed refactored code to verify semantic safety.

### Step 5: Exporting Reports
- Click **"Export Reports"** in the top-right header:
  - Download Explanation Report (`.md`)
  - Download Dependency Graph (`.json`)
  - Download Coverage Report (`.json`)
  - Download Modernization Patch (`.patch`)
  - Download Full Project Audit (`.json`)

---

## 🏆 Key Architectural Highlights for Judges

| Feature | CodeOracle Implementation |
|---|---|
| **Zero Code Execution on Host** | Untrusted code executes **only** inside Docker containers with `--network none` |
| **Real Coverage Guarantee** | Measured with `coverage.py` and Istanbul; never estimated |
| **Non-Destructive Modernization** | Original source files are untouched in `{job_dir}/`; refactored code is generated into `{job_dir}/refactored/` |
| **AST Symbol Diffing** | Checks parameter names/counts and return types; escalates warning severity using dependency graph |
| **Zero Database Footprint** | Client-side direct downloads; stateless backend architecture |
