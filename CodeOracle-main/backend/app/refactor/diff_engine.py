"""
Diff Engine — Computes unified and line-by-line structured diffs between
original and refactored source code files.
"""
import difflib
from typing import List, Tuple
from app.refactor.schema import FileDiff, DiffLine


class DiffEngine:
    """
    Computes precise additions, deletions, modifications, and structured diff representations.
    """

    def compute_diff(self, file_path: str, orig_text: str, refactored_text: str) -> FileDiff:
        """
        Computes both unified diff string and structured line-by-line DiffLines.
        """
        orig_lines = orig_text.splitlines()
        refactored_lines = refactored_text.splitlines()

        # 1. Compute standard unified diff string
        unified = difflib.unified_diff(
            orig_lines,
            refactored_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
        diff_text = "\n".join(unified)

        # 2. Compute structured line-by-line diff using SequenceMatcher
        matcher = difflib.SequenceMatcher(None, orig_lines, refactored_lines)
        diff_lines: List[DiffLine] = []
        additions = 0
        deletions = 0
        modifications = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for idx, line in enumerate(orig_lines[i1:i2]):
                    diff_lines.append(DiffLine(
                        orig_line_num=i1 + idx + 1,
                        refactored_line_num=j1 + idx + 1,
                        type="same",
                        content=line,
                    ))
            elif tag == "delete":
                for idx, line in enumerate(orig_lines[i1:i2]):
                    deletions += 1
                    diff_lines.append(DiffLine(
                        orig_line_num=i1 + idx + 1,
                        refactored_line_num=None,
                        type="del",
                        content=line,
                    ))
            elif tag == "insert":
                for idx, line in enumerate(refactored_lines[j1:j2]):
                    additions += 1
                    diff_lines.append(DiffLine(
                        orig_line_num=None,
                        refactored_line_num=j1 + idx + 1,
                        type="add",
                        content=line,
                    ))
            elif tag == "replace":
                # For replacement blocks, track matching lines as mod
                del_count = i2 - i1
                ins_count = j2 - j1
                mod_count = min(del_count, ins_count)
                modifications += mod_count

                # Output deleted lines first
                for idx, line in enumerate(orig_lines[i1:i2]):
                    if idx < mod_count:
                        diff_lines.append(DiffLine(
                            orig_line_num=i1 + idx + 1,
                            refactored_line_num=None,
                            type="mod",
                            content=f"- {line}",
                        ))
                    else:
                        deletions += 1
                        diff_lines.append(DiffLine(
                            orig_line_num=i1 + idx + 1,
                            refactored_line_num=None,
                            type="del",
                            content=line,
                        ))

                # Output inserted lines next
                for idx, line in enumerate(refactored_lines[j1:j2]):
                    if idx < mod_count:
                        diff_lines.append(DiffLine(
                            orig_line_num=None,
                            refactored_line_num=j1 + idx + 1,
                            type="mod",
                            content=f"+ {line}",
                        ))
                    else:
                        additions += 1
                        diff_lines.append(DiffLine(
                            orig_line_num=None,
                            refactored_line_num=j1 + idx + 1,
                            type="add",
                            content=line,
                        ))

        return FileDiff(
            path=file_path,
            additions=additions,
            deletions=deletions,
            modifications=modifications,
            diff_text=diff_text,
            diff_lines=diff_lines,
        )


# Global singleton
diff_engine = DiffEngine()
