"""
Breaking Change Detector — Performs AST symbol diffing between original and refactored code,
checking function signatures, classes, parameters, return types, and cross-module dependents in the Dependency Graph.
"""
from typing import List, Optional, Dict, Set
from app.analyzers.base.schema import FileAnalysis, FunctionSymbol, ClassSymbol, ParameterSymbol
from app.graph.schema import DependencyGraph
from app.refactor.schema import BreakingChangeWarning


class BreakingChangeDetector:
    """
    Detects potential backward compatibility breaks introduced during refactoring.
    """

    def detect_breaking_changes(
        self,
        orig_fa: FileAnalysis,
        refactored_fa: FileAnalysis,
        graph: Optional[DependencyGraph] = None,
    ) -> List[BreakingChangeWarning]:
        """
        Compares AST symbols of original file vs refactored file and generates structured warnings.
        """
        warnings: List[BreakingChangeWarning] = []
        file_path = orig_fa.path

        # Find dependent files from dependency graph
        dependents: List[str] = []
        if graph:
            dependents = [
                edge.source for edge in graph.edges
                if edge.target == file_path or edge.target.replace("\\", "/") == file_path.replace("\\", "/")
            ]

        has_dependents = len(dependents) > 0

        # ─── 1. Check Removed Functions ─────────────────────────────────────────
        orig_funcs = {f.name: f for f in orig_fa.functions}
        ref_funcs = {f.name: f for f in refactored_fa.functions}

        for fn_name, orig_fn in orig_funcs.items():
            if fn_name not in ref_funcs:
                # Private helper (starts with _) vs public function
                is_private = fn_name.startswith("_")
                severity = "medium" if is_private else ("critical" if has_dependents else "high")
                warnings.append(BreakingChangeWarning(
                    severity=severity,
                    category="api",
                    file=file_path,
                    symbol=fn_name,
                    explanation=(
                        f"Public function `{fn_name}` was removed or renamed in refactored code. "
                        f"External callers will encounter AttributeError or NameError."
                    ),
                    suggested_mitigation=f"Restore `{fn_name}` or provide a deprecated alias wrapper forwarding to the new implementation.",
                    affected_dependents=dependents,
                ))
            else:
                # Check parameter changes for existing function
                ref_fn = ref_funcs[fn_name]
                param_warnings = self._check_parameter_changes(
                    file_path, fn_name, orig_fn, ref_fn, dependents
                )
                warnings.extend(param_warnings)

                # Check return type changes
                if orig_fn.return_type and ref_fn.return_type and orig_fn.return_type != ref_fn.return_type:
                    warnings.append(BreakingChangeWarning(
                        severity="high" if has_dependents else "medium",
                        category="return_type",
                        file=file_path,
                        symbol=fn_name,
                        explanation=(
                            f"Function `{fn_name}` return type annotation changed from `{orig_fn.return_type}` to `{ref_fn.return_type}`. "
                            f"Callers expecting the previous type contract may fail type checks or runtime assertions."
                        ),
                        suggested_mitigation="Ensure return type changes maintain behavioral compatibility with callers.",
                        affected_dependents=dependents,
                    ))

        # ─── 2. Check Classes and Methods ───────────────────────────────────────
        orig_classes = {c.name: c for c in orig_fa.classes}
        ref_classes = {c.name: c for c in refactored_fa.classes}

        for cls_name, orig_cls in orig_classes.items():
            if cls_name not in ref_classes:
                warnings.append(BreakingChangeWarning(
                    severity="critical" if has_dependents else "high",
                    category="renamed_symbol",
                    file=file_path,
                    symbol=cls_name,
                    explanation=f"Class `{cls_name}` was removed or renamed in the refactored file.",
                    suggested_mitigation=f"Keep class `{cls_name}` or provide a compatibility subclass/alias.",
                    affected_dependents=dependents,
                ))
            else:
                ref_cls = ref_classes[cls_name]
                # Check class methods
                orig_methods = {m.name: m for m in orig_cls.methods}
                ref_methods = {m.name: m for m in ref_cls.methods}

                for m_name, orig_m in orig_methods.items():
                    if m_name not in ref_methods:
                        is_private = m_name.startswith("_") and not (m_name.startswith("__") and m_name.endswith("__"))
                        warnings.append(BreakingChangeWarning(
                            severity="medium" if is_private else ("critical" if has_dependents else "high"),
                            category="api",
                            file=file_path,
                            symbol=f"{cls_name}.{m_name}",
                            explanation=f"Method `{m_name}` on class `{cls_name}` was removed in refactoring.",
                            suggested_mitigation=f"Restore method `{cls_name}.{m_name}` to maintain class API contract.",
                            affected_dependents=dependents,
                        ))
                    else:
                        ref_m = ref_methods[m_name]
                        m_param_warnings = self._check_parameter_changes(
                            file_path, f"{cls_name}.{m_name}", orig_m, ref_m, dependents
                        )
                        warnings.extend(m_param_warnings)

        return warnings

    def _check_parameter_changes(
        self,
        file_path: str,
        symbol_name: str,
        orig_fn: FunctionSymbol,
        ref_fn: FunctionSymbol,
        dependents: List[str],
    ) -> List[BreakingChangeWarning]:
        """
        Compares parameter lists between original and refactored function symbols.
        """
        warnings: List[BreakingChangeWarning] = []
        orig_params = orig_fn.parameters
        ref_params = ref_fn.parameters

        # Filter out self/cls
        clean_orig = [p for p in orig_params if p.name not in ("self", "cls")]
        clean_ref = [p for p in ref_params if p.name not in ("self", "cls")]

        # Count parameters
        if len(clean_ref) > len(clean_orig):
            # Check if newly added parameters have default values
            new_params_without_default = [
                p for p in clean_ref[len(clean_orig):]
                if not p.default_value
            ]
            if new_params_without_default:
                warnings.append(BreakingChangeWarning(
                    severity="critical" if len(dependents) > 0 else "high",
                    category="signature",
                    file=file_path,
                    symbol=symbol_name,
                    explanation=(
                        f"Signature for `{symbol_name}` now accepts {len(clean_ref)} parameters (was {len(clean_orig)}), "
                        f"and new parameter(s) {[p.name for p in new_params_without_default]} lack default values. "
                        f"Existing callers will fail with TypeError: missing required positional argument."
                    ),
                    suggested_mitigation="Provide default values (e.g. `param = None`) for all newly added parameters.",
                    affected_dependents=dependents,
                ))
            else:
                warnings.append(BreakingChangeWarning(
                    severity="low",
                    category="signature",
                    file=file_path,
                    symbol=symbol_name,
                    explanation=(
                        f"Signature for `{symbol_name}` added optional parameter(s) with default values: "
                        f"{[p.name for p in clean_ref[len(clean_orig):]]}. Existing callers remain compatible."
                    ),
                    suggested_mitigation="No mitigation needed; parameter has default fallback.",
                    affected_dependents=dependents,
                ))
        elif len(clean_ref) < len(clean_orig):
            # Parameters removed
            warnings.append(BreakingChangeWarning(
                severity="high",
                category="signature",
                file=file_path,
                symbol=symbol_name,
                explanation=(
                    f"Signature for `{symbol_name}` parameter count reduced from {len(clean_orig)} to {len(clean_ref)}. "
                    f"Existing positional callers passing {len(clean_orig)} arguments will fail with TypeError: too many positional arguments."
                ),
                suggested_mitigation="Preserve unused parameters with a deprecation warning or optional default.",
                affected_dependents=dependents,
            ))

        # Check parameter names (keyword arguments break if renamed)
        orig_names = [p.name for p in clean_orig]
        ref_names = [p.name for p in clean_ref]
        if len(orig_names) == len(ref_names) and orig_names != ref_names:
            diff_params = [f"{o} -> {r}" for o, r in zip(orig_names, ref_names) if o != r]
            warnings.append(BreakingChangeWarning(
                severity="medium",
                category="signature",
                file=file_path,
                symbol=symbol_name,
                explanation=(
                    f"Parameter names in `{symbol_name}` were renamed: {', '.join(diff_params)}. "
                    f"Callers using keyword arguments (`{orig_names[0]}=...`) may encounter TypeError: unexpected keyword argument."
                ),
                suggested_mitigation="Retain original parameter names or accept `**kwargs` compatibility fallback.",
                affected_dependents=dependents,
            ))

        return warnings


# Global singleton
breaking_change_detector = BreakingChangeDetector()
