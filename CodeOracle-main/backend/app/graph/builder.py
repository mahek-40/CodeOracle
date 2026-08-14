import os
from typing import Dict, List, Set, Optional
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis, ImportSymbol
from app.graph.schema import DependencyGraph, GraphNode, GraphEdge


class GraphBuilder:
    """
    Builds a normalized dependency graph from ProjectAnalysis output.
    Only relationships proven by static analysis are included — no invented edges.
    """

    def build(self, project_analysis: ProjectAnalysis) -> DependencyGraph:
        """
        Constructs nodes from analyzed files, then builds edges from
        import statements that resolve to other files within the project.
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # Index all project file paths for resolution
        # key: normalized path, value: path as stored in FileAnalysis
        path_index: Dict[str, str] = {}
        for fa in project_analysis.files:
            norm_path = fa.path.replace("\\", "/")
            path_index[norm_path] = fa.path
            
            # Also index by basename without extension for module-style imports
            base, ext = os.path.splitext(norm_path)
            if ext:
                path_index[base] = fa.path
            
            # Index package __init__ and index files
            if base.endswith("/__init__"):
                pkg_base = base[:-9]
                path_index[pkg_base] = fa.path
            elif base == "__init__":
                path_index[""] = fa.path

            if base.endswith("/index"):
                idx_base = base[:-6]
                path_index[idx_base] = fa.path
            elif base == "index":
                path_index[""] = fa.path

        # Build nodes
        for fa in project_analysis.files:
            node_id = fa.path
            nodes.append(GraphNode(
                id=node_id,
                label=os.path.basename(fa.path),
                language=fa.language,
                path=fa.path,
                total_lines=fa.total_lines,
                num_functions=len(fa.functions) + sum(len(c.methods) for c in fa.classes),
                num_classes=len(fa.classes),
                num_imports=len(fa.imports),
                num_exports=len(fa.exports),
                has_parse_error=fa.parse_error is not None,
            ))

        # Build edges from imports
        edge_set: Set[str] = set()
        edge_counter = 0

        for fa in project_analysis.files:
            source_id = fa.path

            for imp in fa.imports:
                target_id = self._resolve_import(
                    module=imp.module,
                    source_path=fa.path,
                    is_relative=imp.is_relative,
                    path_index=path_index,
                    level=imp.level,
                    names=imp.names,
                )

                if target_id and target_id != source_id:
                    edge_key = f"{source_id}→{target_id}"
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append(GraphEdge(
                            id=f"e{edge_counter}",
                            source=source_id,
                            target=target_id,
                            module=imp.module or (imp.names[0] if imp.names else ""),
                            is_relative=imp.is_relative,
                        ))
                        edge_counter += 1

        # Build adjacency maps
        dependents_map: Dict[str, List[str]] = {n.id: [] for n in nodes}
        dependencies_map: Dict[str, List[str]] = {n.id: [] for n in nodes}

        for edge in edges:
            if edge.source in dependencies_map:
                dependencies_map[edge.source].append(edge.target)
            if edge.target in dependents_map:
                dependents_map[edge.target].append(edge.source)

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            dependents_map=dependents_map,
            dependencies_map=dependencies_map,
        )

    def _resolve_import(
        self,
        module: str,
        source_path: str,
        is_relative: bool,
        path_index: Dict[str, str],
        level: int = 0,
        names: Optional[List[str]] = None,
    ) -> str:
        """
        Attempts to resolve an import module name to a concrete file path
        within the project. Returns the resolved path or empty string.
        Only establishes edges supported by static analysis.
        """
        source_dir = os.path.dirname(source_path).replace("\\", "/")
        candidates: List[str] = []

        # 1. Handle Python `from . import symbol` (module is empty, names provided)
        if not module and is_relative and names:
            for name in names:
                if source_dir:
                    candidates.append(f"{source_dir}/{name}")
                candidates.append(name)

        # 2. Handle Python dot relative imports with level (e.g. from ..foo import bar)
        if level > 0 and module:
            up_dir = source_dir
            if level > 1:
                parts = [p for p in source_dir.split("/") if p]
                up_levels = level - 1
                if up_levels <= len(parts):
                    up_dir = "/".join(parts[:-up_levels])
                else:
                    up_dir = ""
            
            module_as_path = module.replace(".", "/").replace("\\", "/")
            if up_dir:
                candidates.append(f"{up_dir}/{module_as_path}")
            candidates.append(module_as_path)

        # 3. Handle JavaScript/TypeScript relative imports (./ and ../)
        if module.startswith("./") or module.startswith("../"):
            joined = os.path.normpath(os.path.join(source_dir, module)).replace("\\", "/")
            # Remove any leading ../ if relative escaped root
            if joined.startswith("../"):
                joined = joined.lstrip("./")
            candidates.append(joined)

        # 4. Handle root aliases (@/ and ~/)
        if module.startswith("@/") or module.startswith("~/"):
            alias_path = module[2:]
            candidates.append(alias_path)
            candidates.append(f"src/{alias_path}")

        # 5. Standard module resolution (Python dotted paths or clean JS paths)
        if module:
            module_as_path = module.replace(".", "/").replace("\\", "/")
            candidates.append(module_as_path)
            if source_dir:
                candidates.append(f"{source_dir}/{module_as_path}")

        # Determine prioritized extensions based on source file language
        source_ext = os.path.splitext(source_path)[1].lower()
        if source_ext == ".py":
            candidate_exts = [".py", "/__init__.py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", "/index.js", "/index.ts"]
        else:
            candidate_exts = [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", "/index.js", "/index.ts", "/index.tsx", "/index.jsx", "/index.mjs", ".py", "/__init__.py"]

        # Try matching each candidate against indexed paths
        for candidate in candidates:
            cand_clean = candidate.replace("\\", "/").rstrip("/")
            if cand_clean in path_index:
                return path_index[cand_clean]

            # Try candidate extensions
            for ext in candidate_exts:
                key = f"{cand_clean}{ext}"
                if key in path_index:
                    return path_index[key]

        return ""



# Module-level singleton
graph_builder = GraphBuilder()
