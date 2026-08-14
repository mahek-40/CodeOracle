"""
Dependency Manager — Detects and installs project dependencies (Python and JavaScript)
prior to test execution in the isolated sandbox or local test environment.
"""
import os
import sys
import subprocess
from typing import Tuple, Optional, List, Dict


class DependencyManager:
    """
    Scans project workspace for package manifests and installs required dependencies.
    """

    def detect_dependencies(self, job_dir: str, language: str) -> List[Dict[str, str]]:
        """
        Scans workspace for dependency manifest files.
        Returns list of dicts with keys: type, path, rel_dir.
        """
        manifests: List[Dict[str, str]] = []
        lang = language.lower()

        for root, dirs, files in os.walk(job_dir):
            # Skip hidden dirs, virtualenvs, and node_modules
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "__pycache__", "generated_tests", "refactored")]

            rel_dir = os.path.relpath(root, job_dir).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            if lang == "python":
                if "requirements.txt" in files:
                    manifests.append({
                        "type": "requirements.txt",
                        "path": os.path.join(root, "requirements.txt"),
                        "rel_dir": rel_dir,
                    })
                if "pyproject.toml" in files:
                    manifests.append({
                        "type": "pyproject.toml",
                        "path": os.path.join(root, "pyproject.toml"),
                        "rel_dir": rel_dir,
                    })
                if "setup.py" in files:
                    manifests.append({
                        "type": "setup.py",
                        "path": os.path.join(root, "setup.py"),
                        "rel_dir": rel_dir,
                    })
            elif lang in ("javascript", "typescript"):
                if "package.json" in files:
                    manifests.append({
                        "type": "package.json",
                        "path": os.path.join(root, "package.json"),
                        "rel_dir": rel_dir,
                    })

        return manifests

    def install_dependencies(
        self,
        job_dir: str,
        language: str,
        timeout_seconds: int = 120,
    ) -> Tuple[bool, str, str, Optional[str]]:
        """
        Installs dependencies for the target workspace.
        Returns (success, stage, install_logs, error_message).
        """
        manifests = self.detect_dependencies(job_dir, language)
        if not manifests:
            return (
                True,
                "dependency_installation",
                "No dependency manifests (requirements.txt, pyproject.toml, package.json) detected in repository.\n",
                None,
            )

        lang = language.lower()
        combined_logs = []

        if lang == "python":
            python_exe = sys.executable
            for m in manifests:
                m_type = m["type"]
                m_path = m["path"]
                cwd = os.path.dirname(m_path)
                combined_logs.append(f"=== Installing Python dependencies from {m['type']} (in ./{m['rel_dir']}) ===")

                if m_type == "requirements.txt":
                    cmd = [python_exe, "-m", "pip", "install", "--no-cache-dir", "-r", m_path]
                elif m_type in ("pyproject.toml", "setup.py"):
                    cmd = [python_exe, "-m", "pip", "install", "--no-cache-dir", "-e", cwd]
                else:
                    continue

                try:
                    res = subprocess.run(
                        cmd,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                    )
                    stdout = res.stdout or ""
                    stderr = res.stderr or ""
                    combined_logs.append(stdout)
                    if stderr:
                        combined_logs.append(f"[STDERR]\n{stderr}")

                    if res.returncode != 0:
                        error_msg = f"Dependency installation failed for {m_type} with exit code {res.returncode}.\n{stderr or stdout}"
                        return False, "dependency_installation", "\n".join(combined_logs), error_msg

                except subprocess.TimeoutExpired:
                    error_msg = f"Dependency installation timed out after {timeout_seconds}s for {m_type}."
                    combined_logs.append(f"[TIMEOUT] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg
                except Exception as exc:
                    error_msg = f"Failed to execute pip install for {m_type}: {str(exc)}"
                    combined_logs.append(f"[ERROR] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg

            return True, "dependency_installation", "\n".join(combined_logs), None

        elif lang in ("javascript", "typescript"):
            for m in manifests:
                cwd = os.path.dirname(m["path"])
                combined_logs.append(f"=== Installing JavaScript dependencies via npm (in ./{m['rel_dir']}) ===")
                cmd = ["npm", "install", "--no-audit", "--no-fund"]
                try:
                    res = subprocess.run(
                        cmd,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                        shell=True,
                    )
                    stdout = res.stdout or ""
                    stderr = res.stderr or ""
                    combined_logs.append(stdout)
                    if stderr:
                        combined_logs.append(f"[STDERR]\n{stderr}")

                    if res.returncode != 0:
                        error_msg = f"npm install failed in ./{m['rel_dir']} with exit code {res.returncode}.\n{stderr or stdout}"
                        return False, "dependency_installation", "\n".join(combined_logs), error_msg

                except subprocess.TimeoutExpired:
                    error_msg = f"npm install timed out after {timeout_seconds}s in ./{m['rel_dir']}."
                    combined_logs.append(f"[TIMEOUT] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg
                except Exception as exc:
                    error_msg = f"Failed to execute npm install in ./{m['rel_dir']}: {str(exc)}"
                    combined_logs.append(f"[ERROR] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg

            return True, "dependency_installation", "\n".join(combined_logs), None

        return True, "dependency_installation", "Unsupported language for dependency manager.\n", None


# Global singleton
dependency_manager = DependencyManager()
