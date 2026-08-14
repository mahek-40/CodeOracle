"""
Explanation schema — normalized output from the AI explanation engine.
Kept separate from the analyzer schema so the AI layer is independently testable.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class SymbolExplanation(BaseModel):
    """Explanation for a single function or class symbol."""
    name: str
    symbol_type: str              # "function" | "class" | "method"
    file_path: str
    start_line: int
    end_line: int
    summary: str
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    side_effects: Optional[str] = None
    edge_cases: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    uncertainty: Optional[str] = None


class FileExplanation(BaseModel):
    """Explanation for a single file/module."""
    path: str
    language: str
    total_lines: int
    summary: str
    purpose: Optional[str] = None
    key_exports: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    symbols: List[SymbolExplanation] = Field(default_factory=list)
    uncertainty: Optional[str] = None
    error: Optional[str] = None   # Set if explanation for this file failed


class ProjectExplanation(BaseModel):
    """Complete hierarchical explanation for a project."""
    overview: str
    languages: List[str] = Field(default_factory=list)
    total_files: int
    total_lines: int
    architecture_summary: Optional[str] = None
    entry_points: List[str] = Field(default_factory=list)
    files: List[FileExplanation] = Field(default_factory=list)
    partial: bool = False           # True if some files failed
    error: Optional[str] = None     # Set if overall explanation failed
