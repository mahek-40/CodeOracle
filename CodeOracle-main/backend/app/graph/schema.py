from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Represents a file/module node in the dependency graph."""
    id: str
    label: str
    language: str
    path: str
    total_lines: int
    num_functions: int
    num_classes: int
    num_imports: int
    num_exports: int
    has_parse_error: bool = False


class GraphEdge(BaseModel):
    """Represents a directional dependency edge between two nodes."""
    id: str
    source: str   # node id (file path)
    target: str   # node id (file path)
    module: str   # the module/package being imported
    is_relative: bool = False


class DependencyGraph(BaseModel):
    """Complete normalized dependency graph for a project."""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    # For quick lookup: {node_id: [node_ids that depend ON it]}
    dependents_map: Dict[str, List[str]] = Field(default_factory=dict)
    # For quick lookup: {node_id: [node_ids it depends on]}
    dependencies_map: Dict[str, List[str]] = Field(default_factory=dict)
