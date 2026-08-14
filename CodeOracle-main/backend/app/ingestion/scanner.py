import os
from typing import Dict, List, Any, Set
from app.ingestion.exceptions import LineLimitExceededError, NoSupportedFilesError

# Directories to ignore
IGNORED_DIRS: Set[str] = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "out",
    "target",
    ".idea",
    ".vscode",
    ".egg-info",
    "coverage",
    "htmlcov",
    ".gitattributes",
}

# File extensions to include for analysis
PYTHON_EXTENSIONS: Set[str] = {".py"}
JAVASCRIPT_EXTENSIONS: Set[str] = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
SUPPORTED_EXTENSIONS: Set[str] = PYTHON_EXTENSIONS | JAVASCRIPT_EXTENSIONS

MAX_SOURCE_LINES = 10000


class ProjectScanner:
    """Scans project directory, detects supported languages, counts source lines, and enforces constraints."""

    def __init__(self, root_dir: str, max_lines: int = MAX_SOURCE_LINES):
        self.root_dir = os.path.abspath(root_dir)
        self.max_lines = max_lines

    def scan(self) -> Dict[str, Any]:
        """
        Walks root_dir, ignores build/venv/git dirs, detects source files,
        counts total lines, and validates line limits.
        """
        source_files: List[Dict[str, Any]] = []
        total_lines = 0
        languages_detected: Set[str] = set()
        file_count = 0

        for current_root, dirs, files in os.walk(self.root_dir):
            # Exclude ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file_name in files:
                ext = os.path.splitext(file_name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(current_root, file_name)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")

                    language = "python" if ext in PYTHON_EXTENSIONS else "javascript"
                    languages_detected.add(language)

                    line_count = self._count_file_lines(full_path)
                    total_lines += line_count
                    file_count += 1

                    source_files.append({
                        "path": rel_path,
                        "language": language,
                        "extension": ext,
                        "lines": line_count,
                        "full_path": full_path,
                    })

        if not source_files:
            raise NoSupportedFilesError()

        if total_lines > self.max_lines:
            raise LineLimitExceededError(line_count=total_lines, limit=self.max_lines)

        return {
            "root_dir": self.root_dir,
            "total_files": file_count,
            "total_lines": total_lines,
            "languages": sorted(list(languages_detected)),
            "files": source_files,
        }

    def _count_file_lines(self, file_path: str) -> int:
        """Counts lines in a source file, ignoring binary file decoding errors."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
