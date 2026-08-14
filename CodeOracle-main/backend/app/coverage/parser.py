"""
Coverage parser — normalizes Python (coverage.py JSON/XML) and JavaScript
(Vitest/Istanbul JSON/LCOV) coverage output files into a unified CoverageReport model.
Never fabricates, estimates, or defaults to 0% when files are missing.
"""
import os
import re
import json
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from app.coverage.schema import FileCoverage, CoverageReport


def _normalize_rel_path(file_path: str, root_dir: Optional[str] = None) -> str:
    """Safely converts an absolute or relative file path to a normalized relative project path."""
    if root_dir:
        try:
            rel = os.path.relpath(file_path, root_dir).replace("\\", "/")
            if not rel.startswith(".."):
                return rel
        except ValueError:
            pass
    return file_path.replace("\\", "/").lstrip("/")


def _is_test_or_internal_file(path: str) -> bool:
    """Helper to filter out test runner and internal generated files from coverage metrics."""
    norm = path.replace("\\", "/").strip("/")
    parts = norm.split("/")
    filename = parts[-1].lower()

    # Check if inside a test directory
    for part in parts[:-1]:
        p_lower = part.lower()
        if p_lower in ("generated_tests", "tests", "test", "__tests__", "coverage", ".pytest_cache"):
            return True

    # Check filename
    if (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.js")
        or filename.endswith(".test.ts")
        or filename.endswith(".spec.js")
        or filename.endswith(".spec.ts")
        or filename == "__init__.py"
    ):
        return True

    return False


def parse_python_coverage_json(
    coverage_data: Dict[str, Any],
    job_id: str,
    root_dir: Optional[str] = None,
) -> CoverageReport:
    """
    Parses standard coverage.py JSON export format.
    """
    files_map = coverage_data.get("files", {})
    files: List[FileCoverage] = []

    total_statements = 0
    total_covered = 0
    total_missing = 0

    for file_path, data in files_map.items():
        rel_path = _normalize_rel_path(file_path, root_dir)

        if _is_test_or_internal_file(rel_path):
            continue

        summary = data.get("summary", {})
        num_statements = summary.get("num_statements", 0)
        covered_count = summary.get("covered_lines", 0)
        missing_count = summary.get("missing_lines", 0)
        percent = float(summary.get("percent_covered", 0.0))

        executed_lines = data.get("executed_lines", [])
        missing_lines = data.get("missing_lines", [])

        if num_statements > 0:
            total_statements += num_statements
            total_covered += covered_count
            total_missing += missing_count

            files.append(FileCoverage(
                path=rel_path,
                language="python",
                total_lines=num_statements,
                covered_lines_count=covered_count,
                uncovered_lines_count=missing_count,
                coverage_percent=round(percent, 2),
                covered_lines=executed_lines,
                uncovered_lines=missing_lines,
            ))

    overall_pct = (
        round((total_covered / total_statements) * 100.0, 2)
        if total_statements > 0
        else 0.0
    )

    return CoverageReport(
        job_id=job_id,
        language="python",
        total_lines=total_statements,
        total_covered_lines=total_covered,
        total_uncovered_lines=total_missing,
        overall_coverage_percent=overall_pct,
        target_reached=(overall_pct >= 60.0),
        status="completed",
        stage="completed",
        files=files,
        timestamp=time.time(),
    )


def parse_python_coverage_xml(
    xml_content: str,
    job_id: str,
    root_dir: Optional[str] = None,
) -> Optional[CoverageReport]:
    """
    Parses standard Cobertura / coverage.py XML report format.
    """
    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return None

    files: List[FileCoverage] = []
    total_statements = 0
    total_covered = 0
    total_missing = 0

    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename", "")
        rel_path = _normalize_rel_path(filename, root_dir)

        if _is_test_or_internal_file(rel_path):
            continue

        lines = cls.findall(".//line")
        num_statements = len(lines)
        if num_statements == 0:
            continue

        covered_lines = []
        missing_lines = []

        for line_elem in lines:
            line_num = int(line_elem.attrib.get("number", 1))
            hits = int(line_elem.attrib.get("hits", 0))
            if hits > 0:
                covered_lines.append(line_num)
            else:
                missing_lines.append(line_num)

        c_count = len(covered_lines)
        m_count = len(missing_lines)
        pct = round((c_count / num_statements) * 100.0, 2)

        total_statements += num_statements
        total_covered += c_count
        total_missing += m_count

        files.append(FileCoverage(
            path=rel_path,
            language="python",
            total_lines=num_statements,
            covered_lines_count=c_count,
            uncovered_lines_count=m_count,
            coverage_percent=pct,
            covered_lines=covered_lines,
            uncovered_lines=missing_lines,
        ))

    overall_pct = (
        round((total_covered / total_statements) * 100.0, 2)
        if total_statements > 0
        else 0.0
    )

    return CoverageReport(
        job_id=job_id,
        language="python",
        total_lines=total_statements,
        total_covered_lines=total_covered,
        total_uncovered_lines=total_missing,
        overall_coverage_percent=overall_pct,
        target_reached=(overall_pct >= 60.0),
        status="completed",
        stage="completed",
        files=files,
        timestamp=time.time(),
    )


def parse_javascript_coverage_json(
    coverage_data: Dict[str, Any],
    job_id: str,
    root_dir: Optional[str] = None,
) -> CoverageReport:
    """
    Parses Vitest / Istanbul JSON coverage format (e.g. coverage-summary.json or coverage-final.json).
    """
    files: List[FileCoverage] = []
    total_statements = 0
    total_covered = 0
    total_missing = 0

    if "total" in coverage_data:
        for file_path, data in coverage_data.items():
            if file_path == "total":
                continue

            rel_path = _normalize_rel_path(file_path, root_dir)

            if _is_test_or_internal_file(rel_path):
                continue

            lines_info = data.get("lines", {})
            t_lines = lines_info.get("total", 0)
            c_lines = lines_info.get("covered", 0)
            u_lines = t_lines - c_lines
            pct = float(lines_info.get("pct", 0.0))

            if t_lines > 0:
                total_statements += t_lines
                total_covered += c_lines
                total_missing += u_lines

                files.append(FileCoverage(
                    path=rel_path,
                    language="javascript",
                    total_lines=t_lines,
                    covered_lines_count=c_lines,
                    uncovered_lines_count=u_lines,
                    coverage_percent=round(pct, 2),
                    covered_lines=[],
                    uncovered_lines=[],
                ))
    else:
        for file_path, data in coverage_data.items():
            rel_path = _normalize_rel_path(file_path, root_dir)

            if _is_test_or_internal_file(rel_path):
                continue

            s_map = data.get("statementMap", {})
            s_counts = data.get("s", {})

            covered_lines = []
            uncovered_lines = []

            for s_id, loc in s_map.items():
                start_line = loc.get("start", {}).get("line", 1)
                count = s_counts.get(s_id, 0)
                if count > 0:
                    covered_lines.append(start_line)
                else:
                    uncovered_lines.append(start_line)

            covered_unique = sorted(list(set(covered_lines)))
            uncovered_unique = [l for l in sorted(list(set(uncovered_lines))) if l not in covered_unique]
            total = len(covered_unique) + len(uncovered_unique)
            pct = (len(covered_unique) / total * 100.0) if total > 0 else 0.0

            if total > 0:
                total_statements += total
                total_covered += len(covered_unique)
                total_missing += len(uncovered_unique)

                files.append(FileCoverage(
                    path=rel_path,
                    language="javascript",
                    total_lines=total,
                    covered_lines_count=len(covered_unique),
                    uncovered_lines_count=len(uncovered_unique),
                    coverage_percent=round(pct, 2),
                    covered_lines=covered_unique,
                    uncovered_lines=uncovered_unique,
                ))

    overall_pct = (
        round((total_covered / total_statements) * 100.0, 2)
        if total_statements > 0
        else 0.0
    )

    return CoverageReport(
        job_id=job_id,
        language="javascript",
        total_lines=total_statements,
        total_covered_lines=total_covered,
        total_uncovered_lines=total_missing,
        overall_coverage_percent=overall_pct,
        target_reached=(overall_pct >= 60.0),
        status="completed",
        stage="completed",
        files=files,
        timestamp=time.time(),
    )


def parse_javascript_lcov(
    lcov_content: str,
    job_id: str,
    root_dir: Optional[str] = None,
) -> Optional[CoverageReport]:
    """
    Parses LCOV format (lcov.info) from Vitest / Jest coverage.
    """
    files: List[FileCoverage] = []
    total_statements = 0
    total_covered = 0
    total_missing = 0

    current_file = None
    covered_lines = []
    missing_lines = []

    for line in lcov_content.splitlines():
        line = line.strip()
        if line.startswith("SF:"):
            current_file = _normalize_rel_path(line[3:], root_dir)
            covered_lines = []
            missing_lines = []
        elif line.startswith("DA:") and current_file:
            parts = line[3:].split(",")
            if len(parts) >= 2:
                line_num = int(parts[0])
                hits = int(parts[1])
                if hits > 0:
                    covered_lines.append(line_num)
                else:
                    missing_lines.append(line_num)
        elif line == "end_of_record" and current_file:
            if not _is_test_or_internal_file(current_file):
                t_count = len(covered_lines) + len(missing_lines)
                c_count = len(covered_lines)
                m_count = len(missing_lines)
                pct = (c_count / t_count * 100.0) if t_count > 0 else 0.0

                if t_count > 0:
                    total_statements += t_count
                    total_covered += c_count
                    total_missing += m_count

                    files.append(FileCoverage(
                        path=current_file,
                        language="javascript",
                        total_lines=t_count,
                        covered_lines_count=c_count,
                        uncovered_lines_count=m_count,
                        coverage_percent=round(pct, 2),
                        covered_lines=covered_lines,
                        uncovered_lines=missing_lines,
                    ))
            current_file = None

    overall_pct = (
        round((total_covered / total_statements) * 100.0, 2)
        if total_statements > 0
        else 0.0
    )

    return CoverageReport(
        job_id=job_id,
        language="javascript",
        total_lines=total_statements,
        total_covered_lines=total_covered,
        total_uncovered_lines=total_missing,
        overall_coverage_percent=overall_pct,
        target_reached=(overall_pct >= 60.0),
        status="completed",
        stage="completed",
        files=files,
        timestamp=time.time(),
    )


def parse_coverage_file(
    file_path: str,
    job_id: str,
    language: str = "python",
    root_dir: Optional[str] = None,
) -> Optional[CoverageReport]:
    """Reads and parses a coverage file (JSON, XML, or LCOV) from disk."""
    if not os.path.exists(file_path):
        return None

    try:
        if file_path.endswith(".xml"):
            with open(file_path, "r", encoding="utf-8") as f:
                return parse_python_coverage_xml(f.read(), job_id, root_dir)
        elif file_path.endswith(".info") or file_path.endswith(".lcov"):
            with open(file_path, "r", encoding="utf-8") as f:
                return parse_javascript_lcov(f.read(), job_id, root_dir)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if language.lower() in ("javascript", "typescript"):
                return parse_javascript_coverage_json(data, job_id, root_dir)
            else:
                return parse_python_coverage_json(data, job_id, root_dir)
    except Exception:
        return None
