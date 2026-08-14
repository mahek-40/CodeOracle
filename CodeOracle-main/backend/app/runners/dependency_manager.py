"""
Dependency Manager — Detects and installs project dependencies (Python and JavaScript)
prior to test execution in the isolated sandbox or local test environment.
Features lockfile detection, strict command formatting, cross-platform execution,
dependency caching, and detailed error tracking.
"""
import os
import sys
import time
import shutil
import logging
import subprocess
from typing import Tuple, Optional, List, Dict, Any

logger = logging.getLogger("codeoracle.runners.dependency_manager")


class DependencyManager:
    """
    Scans project workspace for package manifests and installs required dependencies.
    """

    def detect_dependencies(self, job_dir: str, language: str) -> List[Dict[str, Any]]:
        """
        Scans workspace for dependency manifest files.
        Returns list of dicts with keys: type, path, rel_dir, has_lock.
        """
        manifests: List[Dict[str, Any]] = []
        lang = language.lower()

        if not os.path.exists(job_dir) or not os.path.isdir(job_dir):
            return manifests

        for root, dirs, files in os.walk(job_dir):
            # Skip hidden dirs, virtualenvs, and node_modules
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("node_modules", "venv", ".venv", "__pycache__", "generated_tests", "refactored", "dist", "build")
            ]

            rel_dir = os.path.relpath(root, job_dir).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            if lang == "python":
                if "requirements.txt" in files:
                    manifests.append({
                        "type": "requirements.txt",
                        "path": os.path.join(root, "requirements.txt"),
                        "rel_dir": rel_dir,
                        "has_lock": False,
                    })
                if "pyproject.toml" in files:
                    manifests.append({
                        "type": "pyproject.toml",
                        "path": os.path.join(root, "pyproject.toml"),
                        "rel_dir": rel_dir,
                        "has_lock": False,
                    })
                if "setup.py" in files:
                    manifests.append({
                        "type": "setup.py",
                        "path": os.path.join(root, "setup.py"),
                        "rel_dir": rel_dir,
                        "has_lock": False,
                    })
            elif lang in ("javascript", "typescript"):
                if "package.json" in files:
                    has_lock = "package-lock.json" in files or "npm-shrinkwrap.json" in files
                    manifests.append({
                        "type": "package.json",
                        "path": os.path.join(root, "package.json"),
                        "rel_dir": rel_dir,
                        "has_lock": has_lock,
                    })

        return manifests

    def _execute_command(
        self,
        cmd: Any,
        cwd: str,
        timeout_seconds: int,
    ) -> Tuple[int, str, str]:
        """
        Executes command safely cross-platform (handling Windows cmd vs POSIX list).
        """
        if isinstance(cmd, str):
            res = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=True,
            )
            return res.returncode, res.stdout or "", res.stderr or ""
        else:
            if sys.platform == "win32":
                cmd_str = " ".join(cmd)
                res = subprocess.run(
                    cmd_str,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    shell=True,
                )
            else:
                res = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    shell=False,
                )
            return res.returncode, res.stdout or "", res.stderr or ""

    def install_dependencies(
        self,
        job_dir: str,
        language: str,
        timeout_seconds: int = 120,
    ) -> Tuple[bool, str, str, Optional[str]]:
        """
        Installs dependencies for the target workspace.
        Never reinstalls dependencies if already installed.
        Returns (success, stage, install_logs, error_message).
        """
        if not os.path.exists(job_dir):
            return False, "dependency_installation", "", f"Job directory '{job_dir}' does not exist."

        t0 = time.perf_counter()
        manifests = self.detect_dependencies(job_dir, language)
        if not manifests:
            return (
                True,
                "dependency_installation",
                "No dependency manifests (requirements.txt, pyproject.toml, package.json) detected in repository. Skipping dependency installation.\n",
                None,
            )

        lang = language.lower()
        combined_logs: List[str] = []

        if lang == "python":
            python_exe = sys.executable
            for m in manifests:
                m_type = m["type"]
                m_path = m["path"]
                cwd = os.path.dirname(m_path)

                if not os.path.exists(cwd) or not os.path.isdir(cwd):
                    continue

                display_rel = m['rel_dir'] or "."

                # Check if already installed
                sentinel = os.path.join(cwd, ".deps_installed")
                if os.path.exists(sentinel):
                    logger.info(f"[PERF] Python dependencies already installed in {cwd}. Skipping pip install.")
                    combined_logs.append(f"Dependencies already installed for {m_type} (in ./{display_rel}). Skipping.\n")
                    continue

                combined_logs.append(f"=== Installing Python dependencies from {m_type} (in ./{display_rel}) ===")

                if m_type == "requirements.txt":
                    cmd = [python_exe, "-m", "pip", "install", "--no-cache-dir", "-r", m_path]
                elif m_type in ("pyproject.toml", "setup.py"):
                    cmd = [python_exe, "-m", "pip", "install", "--no-cache-dir", "-e", cwd]
                else:
                    continue

                cmd_display = " ".join(cmd)
                combined_logs.append(f"[COMMAND] {cmd_display}\n[CWD] {cwd}")
                logger.info(f"Installing Python dependencies: {cmd_display} (CWD: {cwd})")

                try:
                    returncode, stdout, stderr = self._execute_command(cmd, cwd, timeout_seconds)
                    combined_logs.append(f"[EXIT CODE] {returncode}")
                    if stdout:
                        combined_logs.append(f"[STDOUT]\n{stdout}")
                    if stderr:
                        combined_logs.append(f"[STDERR]\n{stderr}")

                    if returncode != 0:
                        error_msg = f"pip install failed for {m_type} in ./{display_rel} with exit code {returncode}.\n{stderr or stdout}"
                        logger.error(error_msg)
                        return False, "dependency_installation", "\n".join(combined_logs), error_msg

                    # Mark as installed
                    try:
                        with open(sentinel, "w") as f:
                            f.write("installed\n")
                    except Exception:
                        pass

                except subprocess.TimeoutExpired:
                    error_msg = f"Dependency installation timed out after {timeout_seconds}s for {m_type}."
                    combined_logs.append(f"[TIMEOUT] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg
                except Exception as exc:
                    error_msg = f"Failed to execute pip install for {m_type}: {str(exc)}"
                    combined_logs.append(f"[ERROR] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg

            duration_s = time.perf_counter() - t0
            logger.info(f"[PERF] Python dependency installation completed in {duration_s:.2f}s")
            return True, "dependency_installation", "\n".join(combined_logs), None

        elif lang in ("javascript", "typescript"):
            for m in manifests:
                cwd = os.path.dirname(m["path"])
                if not os.path.exists(cwd) or not os.path.isdir(cwd):
                    continue

                has_lock = m.get("has_lock", False)
                display_rel = m['rel_dir'] or "."

                # Check if already installed
                node_modules = os.path.join(cwd, "node_modules")
                sentinel = os.path.join(cwd, ".deps_installed")
                if os.path.exists(sentinel) or (os.path.isdir(node_modules) and len(os.listdir(node_modules)) > 0):
                    logger.info(f"[PERF] JavaScript dependencies already installed in {cwd}. Skipping npm install.")
                    combined_logs.append(f"JavaScript dependencies already installed (node_modules present in ./{display_rel}). Skipping.\n")
                    continue

                combined_logs.append(f"=== Installing JavaScript dependencies (in ./{display_rel}) ===")

                if has_lock:
                    cmd_list = ["npm", "ci", "--no-audit", "--no-fund"]
                else:
                    cmd_list = ["npm", "install", "--no-audit", "--no-fund"]

                cmd_display = " ".join(cmd_list)
                combined_logs.append(f"[COMMAND] {cmd_display}\n[CWD] {cwd}")
                logger.info(f"Installing JS dependencies: {cmd_display} (CWD: {cwd})")

                try:
                    returncode, stdout, stderr = self._execute_command(cmd_list, cwd, timeout_seconds)
                    combined_logs.append(f"[EXIT CODE] {returncode}")
                    if stdout:
                        combined_logs.append(f"[STDOUT]\n{stdout}")
                    if stderr:
                        combined_logs.append(f"[STDERR]\n{stderr}")

                    # Fallback on lockfile mismatch
                    if returncode != 0 and has_lock:
                        fallback_cmd = ["npm", "install", "--no-audit", "--no-fund"]
                        fallback_display = " ".join(fallback_cmd)
                        combined_logs.append(f"[FALLBACK] 'npm ci' exited with code {returncode}. Retrying with '{fallback_display}'...")
                        logger.warning(f"'npm ci' failed (code {returncode}). Falling back to 'npm install' in {cwd}")

                        returncode, stdout, stderr = self._execute_command(fallback_cmd, cwd, timeout_seconds)
                        combined_logs.append(f"[FALLBACK EXIT CODE] {returncode}")
                        if stdout:
                            combined_logs.append(f"[STDOUT]\n{stdout}")
                        if stderr:
                            combined_logs.append(f"[STDERR]\n{stderr}")

                    if returncode != 0:
                        error_msg = f"npm install failed in ./{display_rel} with exit code {returncode}.\n{stderr or stdout}"
                        logger.error(error_msg)
                        return False, "dependency_installation", "\n".join(combined_logs), error_msg

                    # Mark as installed
                    try:
                        with open(sentinel, "w") as f:
                            f.write("installed\n")
                    except Exception:
                        pass

                except subprocess.TimeoutExpired:
                    error_msg = f"npm install timed out after {timeout_seconds}s in ./{display_rel}."
                    combined_logs.append(f"[TIMEOUT] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg
                except Exception as exc:
                    error_msg = f"Failed to execute npm install in ./{display_rel}: {str(exc)}"
                    combined_logs.append(f"[ERROR] {error_msg}")
                    return False, "dependency_installation", "\n".join(combined_logs), error_msg

            duration_s = time.perf_counter() - t0
            logger.info(f"[PERF] JS dependency installation completed in {duration_s:.2f}s")
            return True, "dependency_installation", "\n".join(combined_logs), None

        return True, "dependency_installation", "Unsupported language for dependency manager.\n", None


# Global singleton
dependency_manager = DependencyManager()
