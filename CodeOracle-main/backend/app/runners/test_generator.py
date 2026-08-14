"""
Test generator pipeline — uses static analysis context and Gemini to generate
runnable unit test suites (pytest for Python, Vitest for JavaScript).
"""
import os
import re
import ast
import json
import time
from typing import Optional, List, Dict
from app.analyzers.base.schema import ProjectAnalysis, FileAnalysis
from app.graph.schema import DependencyGraph
from app.ai.provider import GeminiProvider, AIProviderError, gemini_provider
from app.ai.context_builder import ContextBuilder, context_builder
from app.ai.test_prompts import python_test_generation_prompt, javascript_test_generation_prompt
from app.runners.schema import GeneratedTestFile, TestGenerationResult

INTER_FILE_DELAY_SECS = 0.2


def _clean_code_blocks(text: str) -> str:
    """Strips markdown code fences (```python ... ```) and extracts raw source code."""
    text = text.strip()
    if text.startswith("```"):
        # Strip opening fence (e.g. ```python, ```javascript, ```)
        lines = text.splitlines()
        if len(lines) > 1 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _estimate_test_count(code: str, language: str) -> int:
    """Estimates the number of test cases defined in the test file."""
    if language == "python":
        # Count def test_...
        return len(re.findall(r"^\s*def\s+test_\w+", code, re.MULTILINE))
    else:
        # Count it( or test(
        return len(re.findall(r"\b(it|test)\s*\(", code))


def _derive_module_name(file_path: str) -> str:
    """Converts a relative file path (e.g. src/utils.py or server.py) into an import identifier."""
    clean_path = file_path.replace("\\", "/")
    if clean_path.endswith(".py"):
        clean_path = clean_path[:-3]
    elif clean_path.endswith((".js", ".ts", ".jsx", ".tsx")):
        clean_path = clean_path.rsplit(".", 1)[0]
    
    # Replace slashes with dots for Python imports or clean path for JS
    return clean_path.replace("/", ".")


class TestGenerator:
    """
    Orchestrates unit test generation using Gemini and hierarchical AST metadata.
    """
    __test__ = False

    def __init__(
        self,
        provider: Optional[GeminiProvider] = None,
        ctx_builder: Optional[ContextBuilder] = None,
    ):
        self._provider = provider or gemini_provider
        self._ctx = ctx_builder or context_builder

    def generate_tests(
        self,
        project: ProjectAnalysis,
        job_dir: str,
        graph: Optional[DependencyGraph] = None,
    ) -> TestGenerationResult:
        """
        Generates runnable unit test files for each source file in the project.
        Saves test files in `{job_dir}/generated_tests/`.
        """
        out_dir = os.path.join(job_dir, "generated_tests")
        os.makedirs(out_dir, exist_ok=True)

        # Primary framework
        primary_lang = project.languages[0] if project.languages else "python"
        framework = "pytest" if primary_lang == "python" else "vitest"

        # Create __init__.py for Python projects to enable discovery
        if "python" in project.languages:
            init_path = os.path.join(out_dir, "__init__.py")
            if not os.path.exists(init_path):
                with open(init_path, "w", encoding="utf-8") as f:
                    f.write("# Generated test suite package\n")

        generated_files: List[GeneratedTestFile] = []
        had_error = False
        overall_error: Optional[str] = None

        # Filter to testable files (ignore existing test files if any)
        testable_files = [
            fa for fa in project.files
            if not (fa.path.startswith("test") or "test_" in fa.path or ".test." in fa.path)
            and (fa.functions or fa.classes)
        ]

        if not testable_files:
            # Fallback to all files if none matched the filter
            testable_files = [fa for fa in project.files if fa.language in ("python", "javascript")]

        if not testable_files:
            return TestGenerationResult(
                job_id=os.path.basename(job_dir),
                status="completed",
                framework=framework,
                total_files=0,
                generated_files=[],
            )

        for fa in testable_files:
            time.sleep(INTER_FILE_DELAY_SECS)
            gen_file = self._generate_file_tests(fa, out_dir, graph, framework)
            if gen_file.error:
                had_error = True
            generated_files.append(gen_file)

        # Write manifest.json
        manifest_path = os.path.join(out_dir, "manifest.json")
        manifest_data = {
            "framework": framework,
            "generated_at": time.time(),
            "files": [f.model_dump() for f in generated_files if not f.error],
        }
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
        except Exception:
            pass

        successful_count = sum(1 for f in generated_files if not f.error)
        status = "completed" if successful_count == len(generated_files) else ("partial" if successful_count > 0 else "failed")
        if status == "failed" and generated_files:
            overall_error = generated_files[0].error

        return TestGenerationResult(
            job_id=os.path.basename(job_dir),
            status=status,
            framework=framework,
            total_files=len(generated_files),
            generated_files=generated_files,
            error=overall_error,
        )

    def _generate_file_tests(
        self,
        fa: FileAnalysis,
        out_dir: str,
        graph: Optional[DependencyGraph],
        framework: str,
    ) -> GeneratedTestFile:
        """Generates unit tests for a single file and saves to disk."""
        file_ctx = self._ctx.build_file_context(fa, graph)
        module_name = _derive_module_name(fa.path)

        if fa.language == "python":
            prompt = python_test_generation_prompt(fa.path, file_ctx, module_name)
            base_name = os.path.basename(fa.path)
            if not base_name.startswith("test_"):
                test_filename = f"test_{base_name}"
            else:
                test_filename = base_name
        else:
            import_path = f"../{fa.path}".replace("\\", "/")
            prompt = javascript_test_generation_prompt(fa.path, file_ctx, import_path, framework)
            base_name = os.path.basename(fa.path)
            stem = base_name.rsplit(".", 1)[0]
            ext = base_name.rsplit(".", 1)[1] if "." in base_name else "js"
            test_filename = f"{stem}.test.{ext}"

        dest_path = os.path.join(out_dir, test_filename)

        try:
            raw_text = self._provider.generate(prompt, temperature=0.1)
            code = _clean_code_blocks(raw_text)

            # Validate generated test file quality & non-trivial assertions
            from app.runners.test_validator import test_validator
            is_valid, val_reason = test_validator.validate_test_code(code, fa.language, fa.path)
            if not is_valid:
                # Retry generation with explicit validation error context
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"CRITICAL FIX: Your previous generated test was rejected because: {val_reason}\n"
                    "You MUST write real, executable test functions with valid assertions against the target module. Do not use placeholders or trivial 'assert True'."
                )
                try:
                    retry_text = self._provider.generate(retry_prompt, temperature=0.1)
                    retry_code = _clean_code_blocks(retry_text)
                    retry_valid, retry_reason = test_validator.validate_test_code(retry_code, fa.language, fa.path)
                    if retry_valid:
                        code = retry_code
                    else:
                        return GeneratedTestFile(
                            path=os.path.join("generated_tests", test_filename).replace("\\", "/"),
                            filename=test_filename,
                            target_file=fa.path,
                            language=fa.language,
                            content="",
                            error=f"Test quality validation failed: {retry_reason or val_reason}",
                        )
                except Exception as exc:
                    return GeneratedTestFile(
                        path=os.path.join("generated_tests", test_filename).replace("\\", "/"),
                        filename=test_filename,
                        target_file=fa.path,
                        language=fa.language,
                        content="",
                        error=f"Test quality validation failed: {val_reason}",
                    )

            # Write validated generated test file to disk
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(code)

            estimated_count = _estimate_test_count(code, fa.language)

            return GeneratedTestFile(
                path=os.path.join("generated_tests", test_filename).replace("\\", "/"),
                filename=test_filename,
                target_file=fa.path,
                language=fa.language,
                content=code,
                num_tests_estimated=estimated_count,
            )

        except AIProviderError as exc:
            return GeneratedTestFile(
                path=os.path.join("generated_tests", test_filename).replace("\\", "/"),
                filename=test_filename,
                target_file=fa.path,
                language=fa.language,
                content="",
                error=f"Test generation failed: {exc.message}",
            )
        except Exception as exc:
            return GeneratedTestFile(
                path=os.path.join("generated_tests", test_filename).replace("\\", "/"),
                filename=test_filename,
                target_file=fa.path,
                language=fa.language,
                content="",
                error=f"Unexpected error generating tests: {str(exc)}",
            )


# Global singleton
test_generator = TestGenerator()
