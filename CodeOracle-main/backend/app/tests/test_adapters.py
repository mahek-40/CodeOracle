import os
import tempfile
import pytest
from app.analyzers.python.adapter import PythonAdapter
from app.analyzers.javascript.adapter import JavaScriptAdapter
from app.analyzers.registry import AdapterRegistry
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis


def test_python_adapter_parsing():
    adapter = PythonAdapter()
    assert adapter.can_handle("server.py")
    assert not adapter.can_handle("index.js")

    py_code = """
import os
from math import sqrt as square_root

class BaseCalculator:
    pass

class Calculator(BaseCalculator):
    \"\"\"Advanced math calculator class.\"\"\"
    def __init__(self, precision: int = 2):
        self.precision = precision

    async def compute_sqrt(self, value: float) -> float:
        res = square_root(value)
        return round(res, self.precision)

def calculate_sum(a: int, b: int = 10) -> int:
    return a + b
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(py_code)
        tmp_path = tmp.name

    try:
        analysis = adapter.parse_file(tmp_path, "calc.py")
        assert analysis.language == "python"
        assert analysis.parse_error is None
        assert len(analysis.imports) == 2
        assert len(analysis.classes) == 2

        calc_cls = next(c for c in analysis.classes if c.name == "Calculator")
        assert "BaseCalculator" in calc_cls.base_classes
        assert len(calc_cls.methods) == 2

        sqrt_method = next(m for m in calc_cls.methods if m.name == "compute_sqrt")
        assert sqrt_method.is_async
        assert sqrt_method.is_method
        assert sqrt_method.return_type == "float"

        sum_func = next(f for f in analysis.functions if f.name == "calculate_sum")
        assert len(sum_func.parameters) == 2
        assert sum_func.parameters[0].name == "a"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_javascript_adapter_parsing():
    adapter = JavaScriptAdapter()
    assert adapter.can_handle("index.js")
    assert adapter.can_handle("App.tsx")
    assert not adapter.can_handle("main.py")

    js_code = """
import React, { useState } from 'react';
import { fetchHealth } from './services/api';
const fs = require('fs');

export default class Logger extends BaseLogger {
    log(msg) {
        console.log(msg);
    }
}

export const processItems = async (items: any[]) => {
    fetchHealth();
    return items.length;
};

module.exports = { Logger };
"""
    with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False, encoding="utf-8") as tmp:
        tmp.write(js_code)
        tmp_path = tmp.name

    try:
        analysis = adapter.parse_file(tmp_path, "App.ts")
        assert analysis.language == "javascript"
        assert analysis.parse_error is None
        assert len(analysis.imports) >= 2
        
        # Verify ESM & CJS imports captured
        react_imp = next((i for i in analysis.imports if i.module == "react"), None)
        assert react_imp is not None

        # Verify exports
        assert len(analysis.exports) >= 2
        
        # Verify function extraction
        func = next(f for f in analysis.functions if f.name == "processItems")
        assert func.is_async
        
        # Verify calls extraction
        assert any(c.callee == "fetchHealth" for c in analysis.calls)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_adapter_registry():
    registry = AdapterRegistry()
    assert registry.get_adapter("test.py").language_name == "python"
    assert registry.get_adapter("test.jsx").language_name == "javascript"
    assert registry.get_adapter("unknown.cpp") is None


def test_analyze_project_end_to_end():
    registry = AdapterRegistry()

    with tempfile.TemporaryDirectory() as tmp_dir:
        py_file = os.path.join(tmp_dir, "main.py")
        js_file = os.path.join(tmp_dir, "app.js")

        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import sys\ndef run():\n    print(sys.version)\n")

        with open(js_file, "w", encoding="utf-8") as f:
            f.write("import axios from 'axios';\nfunction start() { axios.get('/api'); }\n")

        scan_results = {
            "root_dir": tmp_dir,
            "total_files": 2,
            "total_lines": 5,
            "languages": ["javascript", "python"],
            "files": [
                {"path": "main.py", "language": "python", "lines": 3, "full_path": py_file},
                {"path": "app.js", "language": "javascript", "lines": 2, "full_path": js_file},
            ]
        }

        project_analysis = registry.analyze_project(scan_results)

        assert isinstance(project_analysis, ProjectAnalysis)
        assert len(project_analysis.files) == 2
        assert "main.py" in project_analysis.dependencies_summary
        assert "sys" in project_analysis.dependencies_summary["main.py"]
        assert "app.js" in project_analysis.dependencies_summary
        assert "axios" in project_analysis.dependencies_summary["app.js"]
