"""
Explanation engine — orchestrates context building and AI calls.
Features bounded request batching, AST symbol extraction, and high-speed execution.
"""
import time
import logging
from typing import Optional, List
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.graph.schema import DependencyGraph
from app.ai.provider import GeminiProvider, AIProviderError, gemini_provider
from app.ai.context_builder import ContextBuilder, context_builder
from app.ai.prompts import repo_overview_prompt, file_explanation_prompt
from app.ai.schema import (
    ProjectExplanation, FileExplanation, SymbolExplanation
)

logger = logging.getLogger("codeoracle.ai.engine")
MAX_EXPLAIN_FILES = 8


class ExplanationEngine:
    """
    Hierarchical explanation engine.
    - Step 1: generate a repository overview from a compact summary.
    - Step 2: per file, generate file-level explanations with symbol details in a single bounded pass.
    Each call is bounded and fast.
    """

    def __init__(
        self,
        provider: Optional[GeminiProvider] = None,
        ctx_builder: Optional[ContextBuilder] = None,
    ):
        self._provider = provider or gemini_provider
        self._ctx = ctx_builder or context_builder

    def explain_project(
        self,
        project: ProjectAnalysis,
        graph: Optional[DependencyGraph] = None,
    ) -> ProjectExplanation:
        """
        Generate a complete hierarchical explanation for a project.
        Returns partial results on partial failures, marks them clearly.
        """
        t0 = time.perf_counter()
        logger.info(f"[PERF] Starting project explanation for {len(project.files)} files")

        # --- 1. Repository overview ---
        repo_ctx = self._ctx.build_repo_context(project, graph)
        prompt = repo_overview_prompt(repo_ctx)
        try:
            overview_text = self._provider.generate(prompt)
        except AIProviderError as exc:
            logger.error(f"[PERF] Overview generation failed: {exc.message}")
            return ProjectExplanation(
                overview="",
                languages=project.languages,
                total_files=project.total_files,
                total_lines=project.total_lines,
                error=f"Repository overview failed: {exc.message}",
            )

        # --- 2. Per-file explanations ---
        file_explanations: List[FileExplanation] = []
        had_error = False

        # Sort files prioritizing entry points and core logic files first
        entry_points = _heuristic_entry_points(project)
        sorted_files = sorted(
            project.files,
            key=lambda fa: (0 if fa.path in entry_points else 1, -fa.total_lines)
        )

        for i, fa in enumerate(sorted_files):
            if i < MAX_EXPLAIN_FILES:
                fe = self._explain_file(fa, graph)
            else:
                # Fast AST summary for remaining files without extra API round trips
                fe = self._fast_ast_file_summary(fa)

            if fe.error:
                had_error = True
            file_explanations.append(fe)

        total_duration = time.perf_counter() - t0
        logger.info(f"[PERF] Completed project explanation in {total_duration:.2f}s (files: {len(file_explanations)})")

        return ProjectExplanation(
            overview=overview_text,
            languages=project.languages,
            total_files=project.total_files,
            total_lines=project.total_lines,
            files=file_explanations,
            entry_points=entry_points,
            partial=had_error,
        )

    def _explain_file(
        self,
        fa: FileAnalysis,
        graph: Optional[DependencyGraph] = None,
    ) -> FileExplanation:
        """Generate explanation for a single file + synthesize symbol details."""
        file_ctx = self._ctx.build_file_context(fa, graph)
        prompt = file_explanation_prompt(file_ctx)

        try:
            file_text = self._provider.generate(prompt)
        except AIProviderError as exc:
            return FileExplanation(
                path=fa.path,
                language=fa.language,
                total_lines=fa.total_lines,
                summary="",
                error=f"File explanation failed: {exc.message}",
            )

        key_exports = [ex.name for ex in fa.exports[:10]]
        deps = [imp.module for imp in fa.imports[:10]]

        # Construct structured symbol explanations from AST metadata and signatures
        symbols: List[SymbolExplanation] = []
        for cls in fa.classes:
            doc = cls.docstring or f"Class '{cls.name}' defining {len(cls.methods)} methods."
            symbols.append(SymbolExplanation(
                name=cls.name,
                symbol_type="class",
                file_path=fa.path,
                start_line=cls.start_line,
                end_line=cls.end_line,
                summary=doc,
                dependencies=[b for b in cls.base_classes if b],
            ))
            for m in cls.methods[:5]:
                m_doc = m.docstring or f"Method '{m.name}' in class '{cls.name}'."
                symbols.append(SymbolExplanation(
                    name=f"{cls.name}.{m.name}",
                    symbol_type="method",
                    file_path=fa.path,
                    start_line=m.start_line,
                    end_line=m.end_line,
                    summary=m_doc,
                    dependencies=list({c.callee for c in getattr(m, "calls", [])})[:5],
                ))

        for fn in fa.functions:
            param_names = [getattr(p, "name", str(p)) for p in fn.parameters] if fn.parameters else []
            fn_doc = fn.docstring or f"Function '{fn.name}' accepting ({', '.join(param_names) if param_names else 'no arguments'})."
            symbols.append(SymbolExplanation(
                name=fn.name,
                symbol_type="function",
                file_path=fa.path,
                start_line=fn.start_line,
                end_line=fn.end_line,
                summary=fn_doc,
                dependencies=list({c.callee for c in getattr(fn, "calls", [])})[:5],
            ))

        return FileExplanation(
            path=fa.path,
            language=fa.language,
            total_lines=fa.total_lines,
            summary=file_text,
            key_exports=key_exports,
            dependencies=deps,
            symbols=symbols,
        )

    def _fast_ast_file_summary(self, fa: FileAnalysis) -> FileExplanation:
        """Fast AST-derived summary for auxiliary files without network calls."""
        key_exports = [ex.name for ex in fa.exports[:10]]
        deps = [imp.module for imp in fa.imports[:10]]
        fn_names = [f.name for f in fa.functions]
        cls_names = [c.name for c in fa.classes]

        summary_parts = [f"Module containing {fa.total_lines} lines of {fa.language}."]
        if cls_names:
            summary_parts.append(f"Defines classes: {', '.join(cls_names)}.")
        if fn_names:
            summary_parts.append(f"Defines functions: {', '.join(fn_names)}.")
        if deps:
            summary_parts.append(f"Imports dependencies: {', '.join(deps[:5])}.")

        summary = " ".join(summary_parts)

        symbols: List[SymbolExplanation] = []
        for fn in fa.functions:
            symbols.append(SymbolExplanation(
                name=fn.name,
                symbol_type="function",
                file_path=fa.path,
                start_line=fn.start_line,
                end_line=fn.end_line,
                summary=fn.docstring or f"Function '{fn.name}' with {len(fn.parameters)} parameters.",
                dependencies=list({c.callee for c in getattr(fn, "calls", [])})[:5],
            ))

        return FileExplanation(
            path=fa.path,
            language=fa.language,
            total_lines=fa.total_lines,
            summary=summary,
            key_exports=key_exports,
            dependencies=deps,
            symbols=symbols,
        )


def _heuristic_entry_points(project: ProjectAnalysis) -> List[str]:
    """
    Heuristically identify entry-point files by name convention.
    No AI call — pure static heuristic.
    """
    entry_names = {"main", "index", "app", "server", "run", "__main__"}
    results = []
    for fa in project.files:
        base = fa.path.replace("\\", "/").split("/")[-1]
        stem = base.rsplit(".", 1)[0].lower()
        if stem in entry_names:
            results.append(fa.path)
    return results


# Module-level singleton
explanation_engine = ExplanationEngine()
