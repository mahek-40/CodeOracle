"""
Phase 4 tests — context building and response parsing, no live Gemini calls.
All AI provider calls are mocked at the GeminiProvider level.
"""
import io
import zipfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.context_builder import ContextBuilder
from app.ai.engine import ExplanationEngine, _heuristic_entry_points
from app.ai.provider import (
    GeminiProvider, AIKeyMissingError, AIQuotaError,
    AITimeoutError, AIServiceError, AIResponseError,
)
from app.ai.prompts import repo_overview_prompt, file_explanation_prompt, symbol_explanation_prompt
from app.ai.schema import ProjectExplanation
from app.analyzers.base.schema import (
    ProjectAnalysis, FileAnalysis, ImportSymbol, ExportSymbol,
    FunctionSymbol, ClassSymbol, ParameterSymbol, FunctionCall,
)
from app.graph.schema import DependencyGraph, GraphNode, GraphEdge

client = TestClient(app)


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_file_analysis(
    path="main.py", language="python", lines=50,
    imports=None, exports=None, functions=None, classes=None,
) -> FileAnalysis:
    return FileAnalysis(
        path=path,
        language=language,
        total_lines=lines,
        imports=imports or [],
        exports=exports or [],
        functions=functions or [],
        classes=classes or [],
    )


def make_project(files=None) -> ProjectAnalysis:
    files = files or [make_file_analysis()]
    return ProjectAnalysis(
        root_dir="/tmp/test",
        total_files=len(files),
        total_lines=sum(f.total_lines for f in files),
        languages=list({f.language for f in files}),
        files=files,
    )


def make_graph() -> DependencyGraph:
    return DependencyGraph(
        nodes=[GraphNode(id="main.py", label="main.py", language="python",
                         path="main.py", total_lines=50, num_functions=1,
                         num_classes=0, num_imports=1, num_exports=0)],
        edges=[],
        total_nodes=1,
        total_edges=0,
        dependents_map={"main.py": []},
        dependencies_map={"main.py": []},
    )


# ─── ContextBuilder Tests ────────────────────────────────────────────────────

def test_context_builder_repo_context_contains_language():
    pa = make_project()
    ctx = ContextBuilder().build_repo_context(pa)
    assert "python" in ctx.lower()


def test_context_builder_repo_context_bounded():
    """Repo context must not exceed MAX_CHARS_REPO_SUMMARY."""
    pa = make_project([make_file_analysis(path=f"file{i}.py", lines=100) for i in range(50)])
    ctx = ContextBuilder().build_repo_context(pa)
    assert len(ctx) <= 1600  # slightly above constant due to truncation at char level


def test_context_builder_file_context_contains_imports():
    fa = make_file_analysis(
        imports=[ImportSymbol(module="os", line=1), ImportSymbol(module="sys", line=2)],
    )
    ctx = ContextBuilder().build_file_context(fa)
    assert "os" in ctx
    assert "sys" in ctx


def test_context_builder_file_context_bounded():
    """File context must not exceed MAX_CHARS_PER_FILE."""
    fa = make_file_analysis(
        functions=[
            FunctionSymbol(name=f"fn{i}", start_line=i*3, end_line=i*3+2,
                           parameters=[ParameterSymbol(name=f"arg{i}", type_annotation="str")])
            for i in range(50)
        ]
    )
    ctx = ContextBuilder().build_file_context(fa)
    assert len(ctx) <= 3100  # just above constant


def test_context_builder_file_context_with_classes():
    fa = make_file_analysis(
        classes=[ClassSymbol(name="MyClass", start_line=5, end_line=30,
                             base_classes=["BaseClass"],
                             methods=[FunctionSymbol(name="run", start_line=10, end_line=20)])],
    )
    ctx = ContextBuilder().build_file_context(fa)
    assert "MyClass" in ctx
    assert "run" in ctx
    assert "BaseClass" in ctx


def test_context_builder_symbol_context_function():
    fa = make_file_analysis(
        functions=[FunctionSymbol(
            name="process", start_line=5, end_line=20,
            parameters=[ParameterSymbol(name="data", type_annotation="dict")],
            return_type="bool",
        )]
    )
    ctx = ContextBuilder().build_symbol_context(fa, "process")
    assert "process" in ctx
    assert "data" in ctx


def test_context_builder_symbol_not_found():
    fa = make_file_analysis()
    ctx = ContextBuilder().build_symbol_context(fa, "nonexistent_fn")
    assert "not found" in ctx.lower()


def test_context_builder_includes_graph_deps():
    pa = make_project([
        make_file_analysis("main.py"),
        make_file_analysis("utils.py"),
    ])
    graph = DependencyGraph(
        nodes=[], edges=[],
        total_nodes=2, total_edges=1,
        dependencies_map={"main.py": ["utils.py"], "utils.py": []},
        dependents_map={"main.py": [], "utils.py": ["main.py"]},
    )
    ctx = ContextBuilder().build_file_context(pa.files[0], graph)
    assert "utils.py" in ctx


# ─── Prompt Template Tests ────────────────────────────────────────────────────

def test_repo_overview_prompt_contains_context():
    ctx = "Languages: python\nFiles: 3"
    prompt = repo_overview_prompt(ctx)
    assert "python" in prompt
    assert "Purpose" in prompt
    assert "Uncertainty" in prompt


def test_file_explanation_prompt_contains_context():
    ctx = "File: server.py\nLanguage: python"
    prompt = file_explanation_prompt(ctx)
    assert "server.py" in prompt
    assert "Purpose" in prompt


def test_symbol_explanation_prompt_for_function():
    ctx = "Function: run\nFile: server.py"
    prompt = symbol_explanation_prompt(ctx, "function")
    assert "function" in prompt.lower()
    assert "run" in prompt or "Inputs" in prompt


# ─── ExplanationEngine Tests (mocked provider) ───────────────────────────────

def make_mock_provider(return_text="Mocked explanation.") -> GeminiProvider:
    provider = MagicMock(spec=GeminiProvider)
    provider.generate.return_value = return_text
    return provider


def test_engine_explain_project_structure():
    pa = make_project([
        make_file_analysis("main.py", functions=[
            FunctionSymbol(name="main", start_line=1, end_line=10)
        ]),
        make_file_analysis("utils.py"),
    ])
    engine = ExplanationEngine(provider=make_mock_provider())
    result = engine.explain_project(pa)

    assert isinstance(result, ProjectExplanation)
    assert result.overview == "Mocked explanation."
    assert len(result.files) == 2
    assert result.error is None
    assert result.partial is False


def test_engine_explain_project_with_graph():
    pa = make_project([make_file_analysis("main.py")])
    graph = make_graph()
    engine = ExplanationEngine(provider=make_mock_provider("OK"))
    result = engine.explain_project(pa, graph)
    assert result.overview == "OK"


def test_engine_returns_error_on_overview_failure():
    pa = make_project()
    provider = MagicMock(spec=GeminiProvider)
    provider.generate.side_effect = AIKeyMissingError()
    engine = ExplanationEngine(provider=provider)
    result = engine.explain_project(pa)

    assert result.error is not None
    assert "GEMINI_API_KEY" in result.error


def test_engine_partial_on_per_file_failure():
    pa = make_project([make_file_analysis("main.py"), make_file_analysis("bad.py")])
    call_count = [0]

    def side_effect(prompt, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:  # overview + first file ok
            return "OK"
        raise AIServiceError("boom")

    provider = MagicMock(spec=GeminiProvider)
    provider.generate.side_effect = side_effect
    engine = ExplanationEngine(provider=provider)
    result = engine.explain_project(pa)

    assert result.partial is True
    error_files = [f for f in result.files if f.error]
    assert len(error_files) >= 1


def test_engine_entry_points_detected():
    pa = make_project([
        make_file_analysis("main.py"),
        make_file_analysis("utils.py"),
        make_file_analysis("index.js", language="javascript"),
    ])
    entry_points = _heuristic_entry_points(pa)
    assert "main.py" in entry_points
    assert "index.js" in entry_points
    assert "utils.py" not in entry_points


# ─── Provider Error Handling ─────────────────────────────────────────────────

def test_provider_raises_key_missing_on_no_key():
    provider = GeminiProvider()
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = ""
        with patch.dict("os.environ", {}, clear=True):
            # Key is absent — _get_client should raise
            with pytest.raises(AIKeyMissingError):
                provider._client = None
                # Override settings to return empty key
                import app.core.config as cfg
                original = cfg.settings.GEMINI_API_KEY
                cfg.settings.GEMINI_API_KEY = ""
                try:
                    provider._get_client()
                finally:
                    cfg.settings.GEMINI_API_KEY = original


# ─── API Endpoint Tests ───────────────────────────────────────────────────────

def _upload_and_get_job_id() -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("main.py", "def main():\n    pass\n")
        z.writestr("utils.py", "def helper(): return 1\n")
    buf.seek(0)
    r = client.post("/api/projects/upload",
                    files={"file": ("test.zip", buf, "application/zip")})
    assert r.status_code == 201
    return r.json()["job_id"]


def test_explain_api_no_key_returns_503():
    job_id = _upload_and_get_job_id()
    with patch("app.api.explain.explanation_engine") as mock_engine:
        mock_engine.explain_project.side_effect = AIKeyMissingError()
        r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "configuration"


def test_explain_api_quota_returns_429():
    job_id = _upload_and_get_job_id()
    with patch("app.api.explain.explanation_engine") as mock_engine:
        mock_engine.explain_project.side_effect = AIQuotaError("exceeded")
        r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 429
    assert r.json()["detail"]["error"] == "quota"


def test_explain_api_timeout_returns_504():
    job_id = _upload_and_get_job_id()
    with patch("app.api.explain.explanation_engine") as mock_engine:
        mock_engine.explain_project.side_effect = AITimeoutError()
        r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 504
    assert r.json()["detail"]["error"] == "timeout"


def test_explain_api_service_error_returns_502():
    job_id = _upload_and_get_job_id()
    with patch("app.api.explain.explanation_engine") as mock_engine:
        mock_engine.explain_project.side_effect = AIServiceError("down")
        r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 502
    assert r.json()["detail"]["error"] == "ai_service"


def test_explain_api_404_on_missing_job():
    r = client.get("/api/jobs/nonexistent-xyz/explain")
    assert r.status_code == 404


def test_explain_api_400_on_pending_job():
    # Create a job but manually leave it in processing state
    from app.jobs.manager import job_manager
    job_id = job_manager.create_job("upload", "test.zip")
    job_manager.update_job(job_id, status="processing", stage="ingestion")
    r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 400


def test_explain_api_success_returns_explanation():
    job_id = _upload_and_get_job_id()
    from app.ai.schema import ProjectExplanation, FileExplanation
    mock_result = ProjectExplanation(
        overview="This is a small Python project.",
        languages=["python"],
        total_files=2,
        total_lines=3,
        files=[
            FileExplanation(path="main.py", language="python", total_lines=2, summary="Entry point."),
            FileExplanation(path="utils.py", language="python", total_lines=1, summary="Utilities."),
        ],
    )
    with patch("app.api.explain.explanation_engine") as mock_engine:
        mock_engine.explain_project.return_value = mock_result
        r = client.get(f"/api/jobs/{job_id}/explain")
    assert r.status_code == 200
    data = r.json()
    assert data["overview"] == "This is a small Python project."
    assert len(data["files"]) == 2
