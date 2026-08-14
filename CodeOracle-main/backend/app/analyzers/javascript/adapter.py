import re
from typing import List, Tuple, Optional, Set
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


def _find_matching_brace_end(lines: List[str], start_idx: int) -> int:
    """Finds 1-indexed ending line for a block starting at start_idx (1-indexed)."""
    brace_count = 0
    found_first_brace = False
    in_block_comment = False

    for line_num in range(start_idx, len(lines) + 1):
        line = lines[line_num - 1]
        i = 0
        while i < len(line):
            if in_block_comment:
                if line[i:i+2] == "*/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if line[i:i+2] == "/*":
                in_block_comment = True
                i += 2
                continue
            if line[i:i+2] == "//":
                break

            ch = line[i]
            if ch in ('"', "'", '`'):
                quote = ch
                i += 1
                while i < len(line):
                    if line[i] == "\\" and i + 1 < len(line):
                        i += 2
                        continue
                    if line[i] == quote:
                        break
                    i += 1
            elif ch == '{':
                brace_count += 1
                found_first_brace = True
            elif ch == '}':
                brace_count -= 1
                if found_first_brace and brace_count <= 0:
                    return line_num
            i += 1

        if found_first_brace and brace_count <= 0:
            return line_num

    return min(start_idx + 1, len(lines))


class JavaScriptAdapter(LanguageAdapter):
    """Language adapter for JavaScript and TypeScript parsing."""

    @property
    def language_name(self) -> str:
        return "javascript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

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

        lines = code.splitlines()
        total_lines = len(lines)

        imports = self._extract_imports(lines)
        exports = self._extract_exports(lines)
        classes, standalone_functions = self._extract_classes_and_functions(lines)
        calls = self._extract_calls(lines)

        return FileAnalysis(
            path=rel_path,
            language=self.language_name,
            total_lines=total_lines,
            imports=imports,
            exports=exports,
            classes=classes,
            functions=standalone_functions,
            calls=calls
        )

    def _extract_imports(self, lines: List[str]) -> List[ImportSymbol]:
        imports: List[ImportSymbol] = []

        # ESM: import { x, y } from 'mod' or import Default from 'mod' or import 'mod'
        esm_pattern = re.compile(
            r"import\s+(?:([\w$\s,{}*]+)\s+from\s+)?['\"]([^'\"]+)['\"]"
        )
        # CJS: const x = require('mod')
        cjs_pattern = re.compile(
            r"(?:const|let|var)\s+(?:([\w$\s,{}]+)\s*=\s*)?require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        )
        # Dynamic import: import('mod')
        dyn_pattern = re.compile(r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if line_str.startswith("//") or line_str.startswith("/*"):
                continue

            esm_match = esm_pattern.search(line_str)
            if esm_match:
                names_part = esm_match.group(1) or ""
                mod = esm_match.group(2)
                imported_names = [
                    n.strip() for n in re.split(r"[,{}\s]+", names_part) if n.strip() and n.strip() != "*"
                ]
                imports.append(ImportSymbol(
                    module=mod,
                    names=imported_names,
                    line=idx,
                    is_relative=mod.startswith("."),
                    level=1 if mod.startswith("./") else (2 if mod.startswith("../") else 0),
                ))
                continue

            cjs_match = cjs_pattern.search(line_str)
            if cjs_match:
                names_part = cjs_match.group(1) or ""
                mod = cjs_match.group(2)
                imported_names = [
                    n.strip() for n in re.split(r"[,{}\s]+", names_part) if n.strip()
                ]
                imports.append(ImportSymbol(
                    module=mod,
                    names=imported_names,
                    line=idx,
                    is_relative=mod.startswith("."),
                    level=1 if mod.startswith("./") else (2 if mod.startswith("../") else 0),
                ))
                continue

            dyn_match = dyn_pattern.search(line_str)
            if dyn_match:
                mod = dyn_match.group(1)
                imports.append(ImportSymbol(
                    module=mod,
                    names=[],
                    line=idx,
                    is_relative=mod.startswith("."),
                    level=1 if mod.startswith("./") else (2 if mod.startswith("../") else 0),
                ))

        return imports

    def _extract_exports(self, lines: List[str]) -> List[ExportSymbol]:
        exports: List[ExportSymbol] = []

        # export default foo / export default class / function
        default_pattern = re.compile(r"export\s+default\s+(?:(?:class|function)\s+)?([\w$]+)?")
        # export const/let/var/function/class name
        named_pattern = re.compile(r"export\s+(?:const|let|var|function|class|async\s+function)\s+([\w$]+)")
        # export { a, b as c }
        named_block_pattern = re.compile(r"export\s*\{([^}]+)\}")
        # module.exports = ...
        cjs_export_pattern = re.compile(r"module\.exports\s*=\s*(?:{[\s\w$,]+}|([\w$]+))")
        # exports.foo = ...
        cjs_named_pattern = re.compile(r"exports\.([\w$]+)\s*=")

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if line_str.startswith("//") or line_str.startswith("/*"):
                continue

            def_match = default_pattern.search(line_str)
            if def_match and "default" in line_str:
                name = def_match.group(1) or "default"
                exports.append(ExportSymbol(name=name, export_type="default", line=idx))
                continue

            named_match = named_pattern.search(line_str)
            if named_match:
                exports.append(ExportSymbol(name=named_match.group(1), export_type="named", line=idx))
                continue

            block_match = named_block_pattern.search(line_str)
            if block_match:
                for n in block_match.group(1).split(","):
                    item = n.strip().split(" as ")[0].strip()
                    if item:
                        exports.append(ExportSymbol(name=item, export_type="named", line=idx))
                continue

            cjs_match = cjs_export_pattern.search(line_str)
            if cjs_match:
                name = cjs_match.group(1) or "module.exports"
                exports.append(ExportSymbol(name=name, export_type="default", line=idx))
                continue

            cjs_n = cjs_named_pattern.search(line_str)
            if cjs_n:
                exports.append(ExportSymbol(name=cjs_n.group(1), export_type="named", line=idx))

        return exports

    def _extract_classes_and_functions(
        self, lines: List[str]
    ) -> Tuple[List[ClassSymbol], List[FunctionSymbol]]:
        classes: List[ClassSymbol] = []
        functions: List[FunctionSymbol] = []

        class_pattern = re.compile(r"class\s+([\w$]+)(?:\s+extends\s+([\w$.]+))?")
        func_pattern = re.compile(
            r"(?:export\s+)?(?:async\s+)?function\s*([\w$]*)\s*\(([^)]*)\)"
        )
        arrow_pattern = re.compile(
            r"(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::\s*[^=]+)?\s*=>"
        )
        fn_expr_pattern = re.compile(
            r"(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?function\s*\(([^)]*)\)"
        )

        class_spans: List[Tuple[int, int]] = []

        # 1. Parse Classes and their internal methods
        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if line_str.startswith("//") or line_str.startswith("/*"):
                continue

            cls_match = class_pattern.search(line_str)
            if cls_match:
                cls_name = cls_match.group(1)
                base_cls = cls_match.group(2)
                bases = [base_cls] if base_cls else []
                end_idx = _find_matching_brace_end(lines, idx)
                class_spans.append((idx, end_idx))

                # Parse methods inside the class body
                methods = self._parse_class_methods(lines, idx, end_idx, cls_name)

                classes.append(ClassSymbol(
                    name=cls_name,
                    base_classes=bases,
                    methods=methods,
                    start_line=idx,
                    end_line=end_idx,
                ))

        # 2. Parse Standalone Functions (outside class bodies)
        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if line_str.startswith("//") or line_str.startswith("/*"):
                continue

            # Skip lines inside class bodies
            if any(start <= idx <= end for start, end in class_spans):
                continue

            func_match = func_pattern.search(line_str)
            if func_match:
                func_name = func_match.group(1) or "anonymous"
                raw_params = func_match.group(2)
                params = self._parse_params(raw_params)
                end_idx = _find_matching_brace_end(lines, idx)
                functions.append(FunctionSymbol(
                    name=func_name,
                    parameters=params,
                    start_line=idx,
                    end_line=end_idx,
                    is_async="async" in line_str,
                    is_method=False,
                ))
                continue

            arrow_match = arrow_pattern.search(line_str)
            if arrow_match:
                func_name = arrow_match.group(1)
                raw_params = arrow_match.group(2)
                params = self._parse_params(raw_params)
                end_idx = _find_matching_brace_end(lines, idx) if "{" in line_str or (idx < len(lines) and "{" in lines[idx]) else idx
                functions.append(FunctionSymbol(
                    name=func_name,
                    parameters=params,
                    start_line=idx,
                    end_line=end_idx,
                    is_async="async" in line_str,
                    is_method=False,
                ))
                continue

            expr_match = fn_expr_pattern.search(line_str)
            if expr_match:
                func_name = expr_match.group(1)
                raw_params = expr_match.group(2)
                params = self._parse_params(raw_params)
                end_idx = _find_matching_brace_end(lines, idx)
                functions.append(FunctionSymbol(
                    name=func_name,
                    parameters=params,
                    start_line=idx,
                    end_line=end_idx,
                    is_async="async" in line_str,
                    is_method=False,
                ))

        return classes, functions

    def _parse_class_methods(
        self, lines: List[str], start_line: int, end_line: int, class_name: str
    ) -> List[FunctionSymbol]:
        """Extracts methods, constructors, and getters/setters within a class body."""
        methods: List[FunctionSymbol] = []
        method_pattern = re.compile(
            r"^\s*(?:(?:static|async|get|set|public|private|protected)\s+)*([\w$]+)\s*\(([^)]*)\)\s*(?::\s*[^;{]+)?\s*\{?"
        )
        reserved = {"if", "for", "while", "switch", "catch", "class", "function", "return"}

        i = start_line
        while i <= end_line:
            line_str = lines[i - 1].strip()
            if line_str.startswith("//") or line_str.startswith("/*") or not line_str:
                i += 1
                continue

            match = method_pattern.match(line_str)
            if match:
                m_name = match.group(1)
                if m_name not in reserved and not m_name.startswith(class_name):
                    raw_params = match.group(2)
                    params = self._parse_params(raw_params)
                    m_end = _find_matching_brace_end(lines, i)
                    methods.append(FunctionSymbol(
                        name=m_name,
                        parameters=params,
                        start_line=i,
                        end_line=m_end,
                        is_async="async" in line_str,
                        is_method=True,
                        class_name=class_name,
                    ))
                    i = max(i + 1, m_end + 1)
                    continue

            i += 1

        return methods

    def _parse_params(self, raw_params: str) -> List[ParameterSymbol]:
        params: List[ParameterSymbol] = []
        if not raw_params.strip():
            return params

        parts = raw_params.split(",")
        for part in parts:
            p = part.strip()
            if not p:
                continue

            # Handle default values: foo: string = "bar"
            default_val = p.split("=")[1].strip() if "=" in p else None
            left_part = p.split("=")[0].strip()

            # Handle type annotations: foo: string
            name_part = left_part.split(":")[0].strip()
            type_annot = left_part.split(":")[1].strip() if ":" in left_part else None

            params.append(ParameterSymbol(
                name=name_part,
                type_annotation=type_annot,
                default_value=default_val
            ))

        return params

    def _extract_calls(self, lines: List[str]) -> List[FunctionCall]:
        calls: List[FunctionCall] = []
        call_pattern = re.compile(r"([\w$.]+)\s*\(([^)]*)\)")
        keywords = {"if", "for", "while", "switch", "catch", "function", "require", "import"}

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if line_str.startswith("//") or line_str.startswith("/*"):
                continue

            for match in call_pattern.finditer(line_str):
                callee = match.group(1)
                if callee not in keywords and not callee.startswith("console."):
                    raw_args = match.group(2)
                    args_count = len([a for a in raw_args.split(",") if a.strip()])
                    calls.append(FunctionCall(
                        callee=callee,
                        args_count=args_count,
                        line=idx
                    ))

        return calls
