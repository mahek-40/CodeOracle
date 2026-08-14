import os
import re
import zipfile
import io
import urllib.request
import urllib.error
import subprocess
from app.ingestion.exceptions import GitHubRepoError
from app.ingestion.zip_handler import ZipHandler

GITHUB_URL_REGEX = re.compile(
    r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)(?:/.*)?$"
)


class GitHubHandler:
    """Handles downloading public GitHub repositories via ZIP codeload archive or shallow git clone."""

    @classmethod
    def download_repo(cls, github_url: str, target_dir: str) -> str:
        """
        Validates public GitHub repository URL, fetches repository contents,
        and extracts into target_dir.
        """
        match = GITHUB_URL_REGEX.match(github_url.strip())
        if not match:
            raise GitHubRepoError(
                "Invalid GitHub URL format. Example valid URL: https://github.com/owner/repository"
            )

        owner = match.group(1)
        repo = match.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]

        # Try zip download first via codeload for main/master/HEAD branches
        branches = ["main", "master", "HEAD"]
        zip_downloaded = False

        for branch in branches:
            archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
            try:
                req = urllib.request.Request(
                    archive_url,
                    headers={"User-Agent": "CodeOracle-App/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    if response.status == 200:
                        content = response.read()
                        ZipHandler.extract_safely(io.BytesIO(content), target_dir)
                        zip_downloaded = True
                        break
            except (urllib.error.HTTPError, urllib.error.URLError):
                continue

        # If codeload zip download failed, attempt git shallow clone fallback
        if not zip_downloaded:
            cls._shallow_git_clone(owner, repo, target_dir)

        # Check that directory is not empty
        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            raise GitHubRepoError("Failed to extract repository or repository is empty.")

        # Flatten nested zip top-level directory if present (e.g. repo-main/)
        cls._flatten_single_subdir(target_dir)

        return target_dir

    @classmethod
    def _shallow_git_clone(cls, owner: str, repo: str, target_dir: str):
        clone_url = f"https://github.com/{owner}/{repo}.git"
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, target_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise GitHubRepoError(
                    f"Repository '{owner}/{repo}' is inaccessible, private, or does not exist."
                )
        except subprocess.TimeoutExpired:
            raise GitHubRepoError("GitHub clone timed out.")
        except Exception as exc:
            if not isinstance(exc, GitHubRepoError):
                raise GitHubRepoError(f"Failed to clone GitHub repository: {str(exc)}")
            raise exc

    @classmethod
    def _flatten_single_subdir(cls, target_dir: str):
        """Delegates directory flattening and metadata cleanup to ZipHandler."""
        ZipHandler._flatten_single_subdir(target_dir)

