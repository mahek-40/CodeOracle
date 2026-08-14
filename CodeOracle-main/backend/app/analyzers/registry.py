from typing import Dict, List, Optional, Any
from app.analyzers.base.adapter import LanguageAdapter
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.analyzers.python.adapter import PythonAdapter
from app.analyzers.javascript.adapter import JavaScriptAdapter


class AdapterRegistry:
    """Registry and orchestrator for pluggable language adapters."""

    def __init__(self):
        self._adapters: List[LanguageAdapter] = []
        # Register default initial adapters
        self.register(PythonAdapter())
        self.register(JavaScriptAdapter())

    def register(self, adapter: LanguageAdapter):
        """Registers a new language adapter."""
        self._adapters.append(adapter)

    def get_adapter(self, file_path: str) -> Optional[LanguageAdapter]:
        """Finds registered adapter capable of handling the file extension."""
        for adapter in self._adapters:
            if adapter.can_handle(file_path):
                return adapter
        return None

    def analyze_project(self, scan_results: Dict[str, Any]) -> ProjectAnalysis:
        """
        Analyzes all source files in a scanned project using registered language adapters.
        Returns normalized ProjectAnalysis object.
        """
        root_dir = scan_results.get("root_dir", "")
        scanned_files = scan_results.get("files", [])
        
        file_analyses: List[FileAnalysis] = []
        dependencies_summary: Dict[str, List[str]] = {}

        for file_info in scanned_files:
            full_path = file_info["full_path"]
            rel_path = file_info["path"]

            adapter = self.get_adapter(rel_path)
            if adapter:
                analysis = adapter.parse_file(full_path, rel_path)
                file_analyses.append(analysis)

                # Record imports in summary
                imported_mods = [imp.module for imp in analysis.imports if imp.module]
                if imported_mods:
                    dependencies_summary[rel_path] = sorted(list(set(imported_mods)))
            else:
                # Unsupported language fallback
                file_analyses.append(FileAnalysis(
                    path=rel_path,
                    language=file_info.get("language", "unknown"),
                    total_lines=file_info.get("lines", 0),
                    parse_error="No registered adapter available for file extension."
                ))

        return ProjectAnalysis(
            root_dir=root_dir,
            total_files=scan_results.get("total_files", len(file_analyses)),
            total_lines=scan_results.get("total_lines", sum(f.total_lines for f in file_analyses)),
            languages=scan_results.get("languages", []),
            files=file_analyses,
            dependencies_summary=dependencies_summary
        )


# Global adapter registry instance
adapter_registry = AdapterRegistry()
