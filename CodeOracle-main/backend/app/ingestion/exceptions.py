class IngestionError(Exception):
    """Base exception for ingestion errors."""
    def __init__(self, message: str, stage: str = "ingestion"):
        super().__init__(message)
        self.message = message
        self.stage = stage


class InvalidZipError(IngestionError):
    """Raised when uploaded file is not a valid ZIP archive."""
    pass


class PathTraversalError(IngestionError):
    """Raised when a ZIP file contains path traversal relative filenames (Zip Slip)."""
    pass


class LineLimitExceededError(IngestionError):
    """Raised when source line count exceeds the 10,000 limit."""
    def __init__(self, line_count: int, limit: int = 10000):
        super().__init__(
            f"Project exceeds line limit: {line_count:,} lines found (maximum allowed is {limit:,}).",
            stage="validation"
        )
        self.line_count = line_count
        self.limit = limit


class NoSupportedFilesError(IngestionError):
    """Raised when no supported source files (Python/JavaScript/TypeScript) are found."""
    def __init__(self):
        super().__init__(
            "No supported Python (.py) or JavaScript/TypeScript (.js, .jsx, .ts, .tsx) files found in project.",
            stage="validation"
        )


class GitHubRepoError(IngestionError):
    """Raised when GitHub repository clone or download fails."""
    pass
