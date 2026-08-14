"""
Explanation engine — orchestrates context building and AI calls.
One file = one bounded Gemini call. No unbounded full-repo dumps.
"""
import time
from typing import Optional, List
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.graph.schema import DependencyGraph
from app.ai.provider import GeminiProvider, AIProviderError, gemini_provider
from app.ai.context_builder import ContextBuilder, context_builder
from app.ai.prompts import repo_overview_prompt, file_explanation_prompt, symbol_explanation_prompt
from app.ai.schema import (
    ProjectExplanation, FileExplanation, SymbolExplanation
)

# How long to pause between per-file calls to avoid rate limits
INTER_FILE_DELAY_SECS = 0.3


class ExplanationEngine:
    """
    Hierarchical explanation engine.
    - Step 1: generate a repository overview from a compact summary.
    - Step 2: per file, generate file-level explanations with symbol details.
    Each call is bounded — never sends >3000 chars per file context.
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
        # --- 1. Repository overview ---
        repo_ctx = self._ctx.build_repo_context(project, graph)
        prompt = repo_overview_prompt(repo_ctx)
        try:
            overview_text = self._provider.generate(prompt)
        except AIProviderError as exc:
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

        for fa in project.files:
            time.sleep(INTER_FILE_DELAY_SECS)
            fe = self._explain_file(fa, graph)
            if fe.error:
                had_error = True
            file_explanations.append(fe)

        # Determine entry points heuristically from the overview context
        entry_points = _heuristic_entry_points(project)

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
        """Generate explanation for a single file + its symbols."""
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

        # Per-symbol explanations (functions and classes)
        symbols: List[SymbolExplanation] = []
        all_symbols: list = list(fa.classes) + list(fa.functions)

        for sym in all_symbols[:10]:  # cap at 10 symbols per file
            time.sleep(INTER_FILE_DELAY_SECS)
            sym_type = "class" if hasattr(sym, "base_classes") else "function"
            sym_ctx = self._ctx.build_symbol_context(fa, sym.name)
            sym_prompt = symbol_explanation_prompt(sym_ctx, sym_type)
            try:
                sym_text = self._provider.generate(sym_prompt)
                symbols.append(SymbolExplanation(
                    name=sym.name,
                    symbol_type=sym_type,
                    file_path=fa.path,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    summary=sym_text,
                    dependencies=list({c.callee for c in getattr(sym, "calls", [])})[:10],
                ))
            except AIProviderError as exc:
                symbols.append(SymbolExplanation(
                    name=sym.name,
                    symbol_type=sym_type,
                    file_path=fa.path,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    summary="",
                    uncertainty=f"Symbol explanation failed: {exc.message}",
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
