"""
Refactoring Engine — Orchestrates modernization analysis, Gemini-driven code refactoring,
AST breaking-change detection, structured diff generation, and risk assessment.
CRITICAL RULE: Original uploaded source files are NEVER overwritten. All refactored code is saved into {job_dir}/refactored/.
"""
import os
import ast
import re
from typing import Optional, List, Dict, Tuple
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.analyzers.python.adapter import PythonAdapter
from app.analyzers.javascript.adapter import JavaScriptAdapter
from app.graph.schema import DependencyGraph

python_adapter = PythonAdapter()
javascript_adapter = JavaScriptAdapter()
from app.ai.provider import GeminiProvider, AIProviderError, gemini_provider
from app.ai.refactor_prompts import python_refactor_prompt, javascript_refactor_prompt
from app.refactor.schema import (
    RefactorResult,
    RefactoredFile,
    FileDiff,
    ModernizationOpportunity,
    BreakingChangeWarning,
    RiskSummary,
)
from app.refactor.diff_engine import DiffEngine, diff_engine
from app.refactor.breaking_detector import BreakingChangeDetector, breaking_change_detector


def _clean_code_blocks(text: str) -> str:
    """Strips markdown code fences (```python ... ```) and extracts raw source code."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 1 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _extract_modernization_opportunities(
    orig_code: str,
    refactored_code: str,
    language: str,
) -> List[ModernizationOpportunity]:
    """
    Heuristically identifies modernization patterns applied between original and refactored code.
    """
    opportunities: List[ModernizationOpportunity] = []

    if language == "python":
        # 1. f-strings upgrade
        if ("%" in orig_code or ".format(" in orig_code) and 'f"' in refactored_code or "f'" in refactored_code:
            opportunities.append(ModernizationOpportunity(
                category="syntax",
                title="String Formatting Upgraded to f-strings",
                description="Replaced legacy % formatting or .format() calls with concise, performant f-strings.",
            ))

        # 2. Type annotations added
        if "->" in refactored_code and "->" not in orig_code:
            opportunities.append(ModernizationOpportunity(
                category="types",
                title="Explicit Type Annotations Added",
                description="Added parameter type hints and return type annotations for enhanced static analysis and IDE autocomplete.",
            ))

        # 3. Context manager usage
        if "with open(" in refactored_code and "open(" in orig_code and "with open(" not in orig_code:
            opportunities.append(ModernizationOpportunity(
                category="structure",
                title="Resource Management with Context Managers",
                description="Enclosed file/resource streams in 'with' context manager blocks for deterministic cleanup.",
            ))

        # 4. Exception handling modernization
        if "raise " in refactored_code and "from " in refactored_code and "from " not in orig_code:
            opportunities.append(ModernizationOpportunity(
                category="error_handling",
                title="Explicit Exception Chaining",
                description="Utilized 'raise ... from err' to preserve the original traceback context.",
            ))

    elif language == "javascript":
        # 1. const/let upgrade
        if "var " in orig_code and ("const " in refactored_code or "let " in refactored_code):
            opportunities.append(ModernizationOpportunity(
                category="syntax",
                title="Replaced 'var' with Block-Scoped 'const'/'let'",
                description="Modernized variable scoping to eliminate hoisting issues and unintended global leaks.",
            ))

        # 2. Arrow functions or async/await
        if "async " in refactored_code and "async " not in orig_code:
            opportunities.append(ModernizationOpportunity(
                category="syntax",
                title="Async/Await Asynchronous Flow",
                description="Modernized asynchronous handling from callback/promise chains to clean async/await.",
            ))

        # 3. Optional chaining / nullish coalescing
        if "?." in refactored_code and "?." not in orig_code:
            opportunities.append(ModernizationOpportunity(
                category="syntax",
                title="Optional Chaining & Nullish Coalescing",
                description="Used '?.' and '??' operators for cleaner, safer property access without verbose conditional guards.",
            ))

    return opportunities


class RefactoringEngine:
    """
    Generates modernized refactor proposals while guaranteeing non-destructive source preservation.
    """

    def __init__(
        self,
        provider: Optional[GeminiProvider] = None,
        differ: Optional[DiffEngine] = None,
        detector: Optional[BreakingChangeDetector] = None,
    ):
        self._provider = provider
        self._differ = differ or diff_engine
        self._detector = detector or breaking_change_detector

    @property
    def provider(self) -> GeminiProvider:
        if self._provider is None:
            self._provider = gemini_provider
        return self._provider

    def generate_refactor(
        self,
        project: ProjectAnalysis,
        job_dir: str,
        graph: Optional[DependencyGraph] = None,
    ) -> RefactorResult:
        """
        Processes project files and outputs modernized code proposals into {job_dir}/refactored/.
        """
        job_id = os.path.basename(job_dir)
        refactored_dir = os.path.join(job_dir, "refactored")
        os.makedirs(refactored_dir, exist_ok=True)

        refactored_files: List[RefactoredFile] = []
        all_warnings: List[BreakingChangeWarning] = []
        all_opportunities: List[ModernizationOpportunity] = []

        total_additions = 0
        total_deletions = 0
        files_modified = 0

        for fa in project.files:
            orig_file_path = os.path.join(job_dir, fa.path)
            if not os.path.exists(orig_file_path):
                continue

            try:
                with open(orig_file_path, "r", encoding="utf-8", errors="replace") as f:
                    orig_code = f.read()
            except Exception:
                continue

            # Build file summary and dependent caller context
            file_summary = f"Functions: {[fn.name for fn in fa.functions]}\nClasses: {[c.name for c in fa.classes]}"
            dependent_callers = ""
            if graph:
                callers = [
                    edge.source for edge in graph.edges
                    if edge.target == fa.path or edge.target.replace("\\", "/") == fa.path.replace("\\", "/")
                ]
                if callers:
                    dependent_callers = f"Modules importing {fa.path}: {', '.join(callers)}"

            # Select prompt based on language
            if fa.language == "javascript":
                prompt = javascript_refactor_prompt(fa.path, file_summary, orig_code, dependent_callers)
            else:
                prompt = python_refactor_prompt(fa.path, file_summary, orig_code, dependent_callers)

            # Generate refactored code with Gemini
            syntax_valid = True
            error_msg = None
            try:
                raw_response = self.provider.generate(prompt, temperature=0.1)
                refactored_code = _clean_code_blocks(raw_response)

                if fa.language == "python":
                    try:
                        ast.parse(refactored_code)
                    except SyntaxError as syn_err:
                        syntax_valid = False
                        error_msg = f"Syntax error in refactored code: {str(syn_err)}"

            except AIProviderError as ai_err:
                # Fallback to original code if AI generation fails
                refactored_code = orig_code
                syntax_valid = False
                error_msg = f"AI Generation error: {ai_err.message}"

            # Save refactored code to {job_dir}/refactored/{fa.path}
            dest_path = os.path.join(refactored_dir, fa.path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(refactored_code)

            # Parse refactored code AST
            if fa.language == "javascript":
                refactored_fa = javascript_adapter.parse_file(dest_path, fa.path)
            else:
                refactored_fa = python_adapter.parse_file(dest_path, fa.path)

            # Detect breaking changes
            warnings = self._detector.detect_breaking_changes(fa, refactored_fa, graph)
            all_warnings.extend(warnings)

            # Compute structured diff
            diff = self._differ.compute_diff(fa.path, orig_code, refactored_code)
            total_additions += diff.additions
            total_deletions += diff.deletions
            if diff.additions > 0 or diff.deletions > 0 or diff.modifications > 0:
                files_modified += 1

            # Extract modernization opportunities
            opps = _extract_modernization_opportunities(orig_code, refactored_code, fa.language)
            all_opportunities.extend(opps)

            refactored_files.append(RefactoredFile(
                path=fa.path,
                language=fa.language,
                original_content=orig_code,
                refactored_content=refactored_code,
                diff=diff,
                opportunities=opps,
                warnings=warnings,
                syntax_valid=syntax_valid,
                error=error_msg,
            ))

        # Compute risk summary
        crit_count = sum(1 for w in all_warnings if w.severity == "critical")
        high_count = sum(1 for w in all_warnings if w.severity == "high")
        med_count = sum(1 for w in all_warnings if w.severity == "medium")
        low_count = sum(1 for w in all_warnings if w.severity == "low")

        safety_score = max(0, 100 - (crit_count * 30 + high_count * 15 + med_count * 5 + low_count * 1))

        if crit_count > 0:
            overall_risk = "critical"
            rec = "Critical breaking changes detected in public APIs. Manual review required before adoption."
        elif high_count > 0:
            overall_risk = "high"
            rec = "High-impact changes to function signatures or class hierarchies detected. Verify caller modules."
        elif med_count > 0:
            overall_risk = "medium"
            rec = "Moderate modernization changes. Run test validation to ensure behavioral equivalence."
        else:
            overall_risk = "low"
            rec = "Clean modernization with minimal risk to existing interfaces."

        risk_summary = RiskSummary(
            overall_risk=overall_risk,
            critical_warnings_count=crit_count,
            high_warnings_count=high_count,
            medium_warnings_count=med_count,
            low_warnings_count=low_count,
            safety_score=safety_score,
            recommendation=rec,
        )

        return RefactorResult(
            job_id=job_id,
            status="completed",
            total_files=len(project.files),
            files_modified=files_modified,
            total_additions=total_additions,
            total_deletions=total_deletions,
            risk_summary=risk_summary,
            files=refactored_files,
            all_warnings=all_warnings,
            all_opportunities=all_opportunities,
        )


# Global singleton
refactoring_engine = RefactoringEngine()
