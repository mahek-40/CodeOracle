from abc import ABC, abstractmethod
from typing import List
from app.analyzers.base.schema import FileAnalysis


class LanguageAdapter(ABC):
    """Abstract base class defining the contract for all pluggable language adapters."""

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Returns normalized language identifier (e.g., 'python', 'javascript')."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Returns list of supported file extensions (e.g. ['.py'])."""
        pass

    def can_handle(self, file_path: str) -> bool:
        """Checks if this adapter handles the given file based on extension."""
        ext = file_path.lower().split('.')[-1]
        return f".{ext}" in self.supported_extensions

    @abstractmethod
    def parse_file(self, full_path: str, rel_path: str) -> FileAnalysis:
        """
        Parses source code file and extracts normalized FileAnalysis.
        Must handle syntax/parsing errors gracefully.
        """
        pass
