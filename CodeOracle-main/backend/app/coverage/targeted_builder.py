"""
Targeted context builder — maps uncovered line numbers from coverage reports
against AST symbols to extract only uncovered functions, methods, and line ranges.
"""
from typing import List, Tuple, Optional
from app.analyzers.base.schema import FileAnalysis, FunctionSymbol, ClassSymbol
from app.coverage.schema import FileCoverage


class TargetedContextBuilder:
    """
    Builds token-efficient, focused prompt context for only the uncovered code regions.
    """

    def build_uncovered_context(
        self,
        fa: FileAnalysis,
        cov: FileCoverage,
    ) -> Tuple[str, List[str]]:
        """
        Intersects uncovered line numbers with AST function and class line boundaries.
        Returns (formatted_context_string, list_of_uncovered_function_names).
        """
        uncovered_set = set(cov.uncovered_lines)
        if not uncovered_set and cov.coverage_percent < 100.0:
            # If uncovered_lines list is empty (e.g. from summary), assume all functions need coverage
            uncovered_set = set(range(1, fa.total_lines + 1))

        targeted_items: List[str] = []
        uncovered_funcs: List[str] = []

        # 1. Inspect standalone functions
        for fn in fa.functions:
            fn_lines = set(range(fn.start_line, fn.end_line + 1))
            missing_in_fn = sorted(list(fn_lines.intersection(uncovered_set)))

            if missing_in_fn or not cov.covered_lines:
                uncovered_funcs.append(fn.name)
                param_str = ", ".join(
                    f"{p.name}: {p.type_annotation}" if p.type_annotation else p.name
                    for p in fn.parameters
                )
                ret_str = f" -> {fn.return_type}" if fn.return_type else ""
                lines_range_str = f"Lines {fn.start_line}-{fn.end_line} (missing: {missing_in_fn[:8]})"

                desc = f"- Function `{fn.name}({param_str}){ret_str}`\n  {lines_range_str}"
                if fn.docstring:
                    desc += f"\n  Docstring: {fn.docstring[:120]}"
                targeted_items.append(desc)

        # 2. Inspect classes and their methods
        for cls in fa.classes:
            cls_uncovered_methods = []
            for method in cls.methods:
                m_lines = set(range(method.start_line, method.end_line + 1))
                missing_in_m = sorted(list(m_lines.intersection(uncovered_set)))
                if missing_in_m or not cov.covered_lines:
                    full_name = f"{cls.name}.{method.name}"
                    uncovered_funcs.append(full_name)
                    param_str = ", ".join(p.name for p in method.parameters)
                    cls_uncovered_methods.append(
                        f"  * Method `{method.name}({param_str})` (missing lines: {missing_in_m[:6]})"
                    )

            if cls_uncovered_methods:
                cls_desc = f"- Class `{cls.name}` (base classes: {cls.base_classes}):\n" + "\n".join(cls_uncovered_methods)
                targeted_items.append(cls_desc)

        # 3. If no specific functions intersected (e.g. top-level module code)
        if not targeted_items:
            missing_summary = sorted(list(uncovered_set))[:20]
            context_str = f"File: {fa.path} has uncovered top-level statements at lines: {missing_summary}."
            return context_str, ["<module_level>"]

        context_str = (
            f"File: {fa.path} (Coverage: {cov.coverage_percent}%, "
            f"Uncovered lines: {cov.uncovered_lines_count}/{cov.total_lines})\n\n"
            + "\n\n".join(targeted_items[:8])  # Bound to max 8 items to stay token-bounded
        )

        return context_str, uncovered_funcs


# Global singleton
targeted_context_builder = TargetedContextBuilder()
