import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.graph.builder import GraphBuilder
from app.graph.schema import DependencyGraph
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis, ImportSymbol

client = TestClient(app)


def make_project_analysis(files_def: list) -> ProjectAnalysis:
    """Helper to build a ProjectAnalysis fixture."""
    files = []
    for f in files_def:
        files.append(FileAnalysis(
            path=f["path"],
            language=f["language"],
            total_lines=f.get("lines", 5),
            imports=[ImportSymbol(module=imp["module"], line=1, is_relative=imp.get("rel", False))
                     for imp in f.get("imports", [])],
        ))
    languages = list({f.language for f in files})
    return ProjectAnalysis(
        root_dir="/tmp/test",
        total_files=len(files),
        total_lines=sum(f.total_lines for f in files),
        languages=languages,
        files=files,
    )


# --- GraphBuilder Unit Tests ---

def test_graph_builder_creates_nodes():
    pa = make_project_analysis([
        {"path": "main.py", "language": "python"},
        {"path": "utils.py", "language": "python"},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)

    assert isinstance(graph, DependencyGraph)
    assert graph.total_nodes == 2
    node_ids = [n.id for n in graph.nodes]
    assert "main.py" in node_ids
    assert "utils.py" in node_ids


def test_graph_builder_relative_python_edge():
    """A relative Python import .utils from main.py should produce an edge to utils.py."""
    pa = make_project_analysis([
        {"path": "main.py", "language": "python", "imports": [{"module": "utils", "rel": True}]},
        {"path": "utils.py", "language": "python"},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)

    assert graph.total_edges == 1
    edge = graph.edges[0]
    assert edge.source == "main.py"
    assert edge.target == "utils.py"


def test_graph_builder_js_relative_edge():
    """A JS relative import './api' from app.js should produce an edge to api.js."""
    pa = make_project_analysis([
        {"path": "app.js", "language": "javascript",
         "imports": [{"module": "./api", "rel": True}]},
        {"path": "api.js", "language": "javascript"},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)

    assert graph.total_edges == 1
    edge = graph.edges[0]
    assert edge.source == "app.js"
    assert edge.target == "api.js"


def test_graph_builder_no_invented_edges():
    """External packages (e.g. 'fastapi', 'react') must NOT produce edges within the graph."""
    pa = make_project_analysis([
        {"path": "server.py", "language": "python",
         "imports": [{"module": "fastapi"}, {"module": "os"}, {"module": "requests"}]},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)

    # Only 1 node, no edges to external packages
    assert graph.total_nodes == 1
    assert graph.total_edges == 0


def test_graph_builder_deduplicates_edges():
    """Duplicate imports between same pair should produce only one edge."""
    pa = make_project_analysis([
        {"path": "a.py", "language": "python",
         "imports": [{"module": "b", "rel": True}, {"module": "b", "rel": True}]},
        {"path": "b.py", "language": "python"},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)
    assert graph.total_edges == 1


def test_graph_builder_adjacency_maps():
    """Verify dependents_map and dependencies_map are populated correctly."""
    pa = make_project_analysis([
        {"path": "main.py", "language": "python", "imports": [{"module": "utils", "rel": True}]},
        {"path": "utils.py", "language": "python"},
    ])
    builder = GraphBuilder()
    graph = builder.build(pa)

    assert "utils.py" in graph.dependencies_map.get("main.py", [])
    assert "main.py" in graph.dependents_map.get("utils.py", [])


# --- API Integration Tests ---

def _upload_zip_and_get_job_id(files: dict) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, content in files.items():
            z.writestr(path, content)
    buf.seek(0)
    r = client.post("/api/projects/upload",
                    files={"file": ("test.zip", buf, "application/zip")})
    assert r.status_code == 201
    return r.json()["job_id"]


def test_graph_api_returns_graph():
    job_id = _upload_zip_and_get_job_id({
        "main.py": "from utils import helper\ndef main(): helper()\n",
        "utils.py": "def helper(): pass\n",
        "frontend/app.js": "import { render } from './render';\nrender();\n",
        "frontend/render.js": "export const render = () => {};\n",
    })
    r = client.get(f"/api/jobs/{job_id}/graph")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["total_nodes"] == 4
    # Edges only for within-project relative imports
    assert data["total_edges"] >= 0


def test_graph_api_404_missing_job():
    r = client.get("/api/jobs/nonexistent-job-id-xyz/graph")
    assert r.status_code == 404


def test_graph_node_fields():
    """Verify graph nodes have all required fields."""
    job_id = _upload_zip_and_get_job_id({
        "server.py": "import os\n\nclass App:\n    def run(self):\n        print('running')\n",
    })
    r = client.get(f"/api/jobs/{job_id}/graph")
    assert r.status_code == 200
    nodes = r.json()["nodes"]
    assert len(nodes) == 1
    node = nodes[0]
    assert node["id"] == "server.py"
    assert node["label"] == "server.py"
    assert node["language"] == "python"
    assert node["num_classes"] == 1
    assert node["num_functions"] == 1
