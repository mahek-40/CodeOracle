"""
Context builder — converts ProjectAnalysis + DependencyGraph into bounded,
hierarchical prompt context suitable for Gemini.

Rules (from Rules.md):
- Never blindly send the whole repository to Gemini.
- Use hierarchical, dependency-aware context.
- Keep prompts bounded.
- Do not remove context that changes code meaning.
"""
from typing import List, Optional, Dict
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis, FunctionSymbol, ClassSymbol
from app.graph.schema import DependencyGraph

# Token-budget proxy: limit characters per file context block
MAX_CHARS_PER_FILE = 3000
MAX_CHARS_REPO_SUMMARY = 1500
MAX_FILES_IN_OVERVIEW = 20


class ContextBuilder:
    """
    Builds hierarchical prompt context strings from static analysis data.
    Never sends raw source code — builds structured summaries from AST facts.
    """

    def build_repo_context(
        self,
        project: ProjectAnalysis,
        graph: Optional[DependencyGraph] = None,
    ) -> str:
        """Returns a bounded repository-level summary for the overview prompt."""
        lines: List[str] = [
            f"Project Summary:",
            f"  Languages: {', '.join(project.languages)}",
            f"  Total files: {project.total_files}",
            f"  Total source lines: {project.total_lines}",
            "",
            "Files (up to 20 shown):",
        ]

        for fa in project.files[:MAX_FILES_IN_OVERVIEW]:
            dep_count = len(project.dependencies_summary.get(fa.path, []))
            graph_deps = ""
            if graph:
                depends_on = graph.dependencies_map.get(fa.path, [])
                depended_by = graph.dependents_map.get(fa.path, [])
                if depends_on:
                    graph_deps = f" → depends on: {', '.join(depends_on[:4])}"
                if depended_by:
                    graph_deps += f" | depended by: {', '.join(depended_by[:4])}"

            fn_count = len(fa.functions) + sum(len(c.methods) for c in fa.classes)
            lines.append(
                f"  {fa.path} ({fa.language}, {fa.total_lines}L, "
                f"{len(fa.classes)} classes, {fn_count} functions){graph_deps}"
            )

        if project.total_files > MAX_FILES_IN_OVERVIEW:
            lines.append(f"  ... and {project.total_files - MAX_FILES_IN_OVERVIEW} more files")

        return "\n".join(lines)[:MAX_CHARS_REPO_SUMMARY]

    def build_file_context(
        self,
        fa: FileAnalysis,
        graph: Optional[DependencyGraph] = None,
    ) -> str:
        """
        Returns a bounded, structured context block for a single file.
        Includes imports, exports, class/method signatures, and function signatures.
        Does NOT include raw source code.
        """
        parts: List[str] = [
            f"File: {fa.path}",
            f"Language: {fa.language}",
            f"Lines: {fa.total_lines}",
        ]

        if fa.parse_error:
            parts.append(f"Parse warning: {fa.parse_error}")

        if fa.imports:
            imp_strs = [
                f"{imp.module}" + (f" (names: {', '.join(imp.names[:5])})" if imp.names else "")
                for imp in fa.imports[:15]
            ]
            parts.append(f"Imports: {'; '.join(imp_strs)}")

        if fa.exports:
            exp_strs = [f"{ex.name} ({ex.export_type})" for ex in fa.exports[:10]]
            parts.append(f"Exports: {'; '.join(exp_strs)}")

        if graph:
            deps = graph.dependencies_map.get(fa.path, [])
            dependents = graph.dependents_map.get(fa.path, [])
            if deps:
                parts.append(f"Depends on (project files): {', '.join(deps[:6])}")
            if dependents:
                parts.append(f"Depended on by: {', '.join(dependents[:6])}")

        # Classes
        for cls in fa.classes:
            bases = f"({', '.join(cls.base_classes)})" if cls.base_classes else ""
            parts.append(f"\nClass {cls.name}{bases} [lines {cls.start_line}-{cls.end_line}]:")
            if cls.docstring:
                parts.append(f"  Docstring: {cls.docstring[:200]}")
            for m in cls.methods[:10]:
                sig = self._format_function_sig(m)
                parts.append(f"  Method {sig} [lines {m.start_line}-{m.end_line}]"
                              + (" [async]" if m.is_async else ""))

        # Standalone functions
        for fn in fa.functions[:20]:
            sig = self._format_function_sig(fn)
            parts.append(f"\nFunction {sig} [lines {fn.start_line}-{fn.end_line}]"
                         + (" [async]" if fn.is_async else ""))
            if fn.docstring:
                parts.append(f"  Docstring: {fn.docstring[:200]}")

        result = "\n".join(parts)
        return result[:MAX_CHARS_PER_FILE]

    def build_symbol_context(
        self,
        fa: FileAnalysis,
        symbol_name: str,
    ) -> str:
        """
        Returns focused context for a single function or class symbol.
        Used for targeted symbol-level explanation prompts.
        """
        # Search functions
        for fn in fa.functions:
            if fn.name == symbol_name:
                return self._function_context_block(fn, fa.path)

        # Search class methods
        for cls in fa.classes:
            if cls.name == symbol_name:
                return self._class_context_block(cls, fa.path)
            for m in cls.methods:
                if m.name == symbol_name:
                    return self._function_context_block(m, fa.path)

        return f"Symbol '{symbol_name}' not found in {fa.path}."

    def _format_function_sig(self, fn: FunctionSymbol) -> str:
        params = ", ".join(
            p.name + (f": {p.type_annotation}" if p.type_annotation else "")
            + (f" = {p.default_value}" if p.default_value else "")
            for p in fn.parameters
        )
        ret = f" -> {fn.return_type}" if fn.return_type else ""
        return f"{fn.name}({params}){ret}"

    def _function_context_block(self, fn: FunctionSymbol, file_path: str) -> str:
        lines = [
            f"Function: {fn.name}",
            f"File: {file_path}",
            f"Lines: {fn.start_line}-{fn.end_line}",
            f"Async: {fn.is_async}",
        ]
        if fn.is_method and fn.class_name:
            lines.append(f"Member of class: {fn.class_name}")
        params = ", ".join(
            p.name + (f": {p.type_annotation}" if p.type_annotation else "")
            + (f" = {p.default_value}" if p.default_value else "")
            for p in fn.parameters
        )
        lines.append(f"Signature: {fn.name}({params})" + (f" -> {fn.return_type}" if fn.return_type else ""))
        if fn.docstring:
            lines.append(f"Docstring: {fn.docstring[:300]}")
        if fn.calls:
            callees = list({c.callee for c in fn.calls[:10]})
            lines.append(f"Calls: {', '.join(callees)}")
        return "\n".join(lines)

    def _class_context_block(self, cls: ClassSymbol, file_path: str) -> str:
        lines = [
            f"Class: {cls.name}",
            f"File: {file_path}",
            f"Lines: {cls.start_line}-{cls.end_line}",
        ]
        if cls.base_classes:
            lines.append(f"Inherits from: {', '.join(cls.base_classes)}")
        if cls.docstring:
            lines.append(f"Docstring: {cls.docstring[:300]}")
        method_sigs = [self._format_function_sig(m) for m in cls.methods[:15]]
        if method_sigs:
            lines.append(f"Methods: {'; '.join(method_sigs)}")
        return "\n".join(lines)



context_builder = ContextBuilder()
