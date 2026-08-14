from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceLocation(BaseModel):
    line: int
    column: Optional[int] = None


class ImportSymbol(BaseModel):
    module: str
    names: List[str] = Field(default_factory=list)
    alias: Optional[str] = None
    line: int
    is_relative: bool = False
    level: int = 0



class ExportSymbol(BaseModel):
    name: str
    export_type: str = "named"  # "named", "default", "all"
    line: int


class ParameterSymbol(BaseModel):
    name: str
    type_annotation: Optional[str] = None
    default_value: Optional[str] = None


class FunctionCall(BaseModel):
    caller: Optional[str] = None
    callee: str
    args_count: int = 0
    line: int


class FunctionSymbol(BaseModel):
    name: str
    parameters: List[ParameterSymbol] = Field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    start_line: int
    end_line: int
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    calls: List[FunctionCall] = Field(default_factory=list)


class ClassSymbol(BaseModel):
    name: str
    base_classes: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    methods: List[FunctionSymbol] = Field(default_factory=list)
    start_line: int
    end_line: int


class FileAnalysis(BaseModel):
    path: str
    language: str
    total_lines: int
    imports: List[ImportSymbol] = Field(default_factory=list)
    exports: List[ExportSymbol] = Field(default_factory=list)
    classes: List[ClassSymbol] = Field(default_factory=list)
    functions: List[FunctionSymbol] = Field(default_factory=list)
    calls: List[FunctionCall] = Field(default_factory=list)
    parse_error: Optional[str] = None


class ProjectAnalysis(BaseModel):
    root_dir: str
    total_files: int
    total_lines: int
    languages: List[str] = Field(default_factory=list)
    files: List[FileAnalysis] = Field(default_factory=list)
    dependencies_summary: Dict[str, List[str]] = Field(default_factory=dict)
