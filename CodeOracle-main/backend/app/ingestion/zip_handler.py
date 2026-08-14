import os
import shutil
import zipfile
from typing import BinaryIO, Union
from app.ingestion.exceptions import InvalidZipError, PathTraversalError


class ZipHandler:
    """Handles safe validation and extraction of uploaded ZIP archives."""

    @staticmethod
    def extract_safely(file_source: Union[str, BinaryIO], target_dir: str) -> str:
        """
        Safely extracts ZIP archive to target_dir after checking for path traversal attacks.
        Returns target_dir on success.
        """
        target_dir_abs = os.path.abspath(target_dir)

        try:
            with zipfile.ZipFile(file_source, 'r') as zip_ref:
                # Validate all members for path traversal (Zip Slip vulnerability)
                for member in zip_ref.infolist():
                    member_path = member.filename
                    
                    # Prevent absolute path or parent relative path escape
                    normalized_parts = member_path.replace("\\", "/").split("/")
                    if member_path.startswith("/") or member_path.startswith("\\") or ".." in normalized_parts:
                        raise PathTraversalError(f"Path traversal detected in ZIP entry: '{member_path}'")

                    resolved_target = os.path.abspath(os.path.join(target_dir_abs, member_path))
                    
                    if not resolved_target.startswith(target_dir_abs + os.sep) and resolved_target != target_dir_abs:
                        raise PathTraversalError(f"Zip extraction path '{resolved_target}' escapes destination '{target_dir_abs}'")

                # Perform actual extraction after safety validation
                zip_ref.extractall(target_dir_abs)

            # Flatten single top-level subdirectory if archive was nested (e.g. repo-main/)
            ZipHandler._flatten_single_subdir(target_dir_abs)

        except zipfile.BadZipFile:
            raise InvalidZipError("Uploaded file is not a valid or readable ZIP archive.")
        except PathTraversalError:
            raise
        except Exception as exc:
            raise InvalidZipError(f"Failed to process ZIP archive: {str(exc)}")

        return target_dir_abs

    @staticmethod
    def _flatten_single_subdir(target_dir: str):
        """If target_dir contains only 1 subdirectory (e.g. repo-main from zip extract), move contents up."""
        for entry in list(os.listdir(target_dir)):
            if entry in ("__MACOSX", ".DS_Store", "Thumbs.db"):
                entry_path = os.path.join(target_dir, entry)
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path, ignore_errors=True)
                else:
                    try:
                        os.remove(entry_path)
                    except Exception:
                        pass

        entries = [os.path.join(target_dir, e) for e in os.listdir(target_dir)]
        if len(entries) == 1 and os.path.isdir(entries[0]):
            single_sub = entries[0]
            for item in os.listdir(single_sub):
                src = os.path.join(single_sub, item)
                dst = os.path.join(target_dir, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    else:
                        try:
                            os.remove(dst)
                        except Exception:
                            pass
                shutil.move(src, dst)
            try:
                shutil.rmtree(single_sub, ignore_errors=True)
            except Exception:
                pass

