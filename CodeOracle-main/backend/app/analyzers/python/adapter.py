import ast
from typing import List, Tuple, Optional, Any
from app.analyzers.base.adapter import LanguageAdapter
from app.analyzers.base.schema import (
    FileAnalysis,
    ImportSymbol,
    ExportSymbol,
    ClassSymbol,
    FunctionSymbol,
    ParameterSymbol,
    FunctionCall,
)


class PythonAdapter(LanguageAdapter):
    """Language adapter for Python using built-in AST module."""

    @property
    def language_name(self) -> str:
        return "python"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py"]

    def parse_file(self, full_path: str, rel_path: str) -> FileAnalysis:
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
        except Exception as exc:
            return FileAnalysis(
                path=rel_path,
                language=self.language_name,
                total_lines=0,
                parse_error=f"Failed to read file: {str(exc)}"
            )

        line_count = len(code.splitlines())

        try:
            tree = ast.parse(code, filename=rel_path)
        except SyntaxError as syn_err:
            return FileAnalysis(
                path=rel_path,
                language=self.language_name,
                total_lines=line_count,
                parse_error=f"SyntaxError at line {syn_err.lineno}: {syn_err.msg}"
            )
        except Exception as exc:
            return FileAnalysis(
                path=rel_path,
                language=self.language_name,
                total_lines=line_count,
                parse_error=f"AST Parse Exception: {str(exc)}"
            )

        imports = self._extract_imports(tree)
        classes, standalone_functions = self._extract_classes_and_functions(tree)
        all_calls = self._extract_calls(tree)
        exports = self._extract_exports(tree, classes, standalone_functions)

        return FileAnalysis(
            path=rel_path,
            language=self.language_name,
            total_lines=line_count,
            imports=imports,
            exports=exports,
            classes=classes,
            functions=standalone_functions,
            calls=all_calls
        )

    def _extract_imports(self, tree: ast.AST) -> List[ImportSymbol]:
        imports: List[ImportSymbol] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportSymbol(
                        module=alias.name,
                        alias=alias.asname,
                        line=getattr(node, 'lineno', 1)
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                imports.append(ImportSymbol(
                    module=module,
                    names=names,
                    line=getattr(node, 'lineno', 1),
                    is_relative=node.level > 0,
                    level=node.level or 0,
                ))
        return imports

    def _extract_classes_and_functions(
        self, tree: ast.Module
    ) -> Tuple[List[ClassSymbol], List[FunctionSymbol]]:
        classes: List[ClassSymbol] = []
        standalone_functions: List[FunctionSymbol] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(self._parse_class_def(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                standalone_functions.append(self._parse_function_def(node, is_method=False))

        return classes, standalone_functions

    def _parse_class_def(self, node: ast.ClassDef) -> ClassSymbol:
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(f"{self._get_name(base.value)}.{base.attr}")

        docstring = ast.get_docstring(node)
        methods: List[FunctionSymbol] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._parse_function_def(item, is_method=True, class_name=node.name))

        start_line = getattr(node, 'lineno', 1)
        end_line = getattr(node, 'end_lineno', start_line)

        return ClassSymbol(
            name=node.name,
            base_classes=base_classes,
            docstring=docstring,
            methods=methods,
            start_line=start_line,
            end_line=end_line
        )

    def _parse_function_def(
        self,
        node: Any,
        is_method: bool = False,
        class_name: Optional[str] = None
    ) -> FunctionSymbol:
        params: List[ParameterSymbol] = []

        num_args = len(node.args.args)
        num_defaults = len(node.args.defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(node.args.args):
            annotation = ast.unparse(arg.annotation) if getattr(arg, 'annotation', None) else None
            default_val = None
            if idx >= default_offset:
                def_node = node.args.defaults[idx - default_offset]
                try:
                    default_val = ast.unparse(def_node)
                except Exception:
                    default_val = "..."
            params.append(ParameterSymbol(name=arg.arg, type_annotation=annotation, default_value=default_val))

        return_type = ast.unparse(node.returns) if getattr(node, 'returns', None) else None
        docstring = ast.get_docstring(node)
        calls = self._extract_calls(node, caller_name=node.name)

        start_line = getattr(node, 'lineno', 1)
        end_line = getattr(node, 'end_lineno', start_line)

        return FunctionSymbol(
            name=node.name,
            parameters=params,
            return_type=return_type,
            docstring=docstring,
            start_line=start_line,
            end_line=end_line,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            class_name=class_name,
            calls=calls
        )

    def _extract_calls(self, node: ast.AST, caller_name: Optional[str] = None) -> List[FunctionCall]:
        calls: List[FunctionCall] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                callee_name = self._get_name(child.func)
                if callee_name:
                    calls.append(FunctionCall(
                        caller=caller_name,
                        callee=callee_name,
                        args_count=len(child.args),
                        line=getattr(child, 'lineno', 1)
                    ))
        return calls

    def _extract_exports(
        self,
        tree: ast.Module,
        classes: List[ClassSymbol],
        functions: List[FunctionSymbol]
    ) -> List[ExportSymbol]:
        exports: List[ExportSymbol] = []
        # Check for __all__
        all_list = None
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(stmt.value, (ast.List, ast.Tuple)):
                            all_list = [
                                elt.value for elt in stmt.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]

        if all_list is not None:
            for name in all_list:
                exports.append(ExportSymbol(name=name, export_type="named", line=1))
        else:
            # Top-level functions & classes are exported in Python
            for cls in classes:
                exports.append(ExportSymbol(name=cls.name, export_type="named", line=cls.start_line))
            for func in functions:
                if not func.name.startswith("_"):
                    exports.append(ExportSymbol(name=func.name, export_type="named", line=func.start_line))

        return exports

    def _get_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""
