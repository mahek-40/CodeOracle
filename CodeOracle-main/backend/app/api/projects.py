import os
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from app.jobs.manager import job_manager
from app.ingestion.zip_handler import ZipHandler
from app.ingestion.github_handler import GitHubHandler
from app.ingestion.scanner import ProjectScanner
from app.ingestion.exceptions import IngestionError
from app.analyzers.registry import adapter_registry

router = APIRouter(prefix="/projects", tags=["Projects"])


class GitHubIngestRequest(BaseModel):
    url: str


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_zip_project(file: UploadFile = File(...)):
    """
    Accepts ZIP file, validates structure and path traversal security,
    extracts to temporary job workspace, scans Python/JavaScript files,
    runs language adapters, and enforces 10,000 source-line limit.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .zip archive."
        )

    job_id = job_manager.create_job("upload", file.filename)
    job_dir = job_manager.get_job_dir(job_id)

    try:
        # Extract ZIP safely
        ZipHandler.extract_safely(file.file, job_dir)

        # Scan files and enforce line limit
        scanner = ProjectScanner(job_dir)
        scan_results = scanner.scan()

        # Run language adapters
        project_analysis = adapter_registry.analyze_project(scan_results)

        job_manager.update_job(
            job_id,
            status="completed",
            stage="analysis",
            stats=project_analysis.model_dump()
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "stage": "analysis",
            "stats": project_analysis.model_dump()
        }

    except IngestionError as exc:
        job_manager.update_job(
            job_id,
            status="failed",
            stage=exc.stage,
            error=exc.message
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "stage": exc.stage,
                "job_id": job_id
            }
        )
    except Exception as exc:
        err_msg = f"Unexpected error during project upload: {str(exc)}"
        job_manager.update_job(job_id, status="failed", stage="analysis", error=err_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": err_msg, "job_id": job_id}
        )


@router.post("/github", status_code=status.HTTP_201_CREATED)
async def ingest_github_project(payload: GitHubIngestRequest):
    """
    Accepts public GitHub repository URL, downloads repository safely,
    scans Python/JavaScript files, runs language adapters, and enforces line limits.
    """
    if not payload.url or "github.com" not in payload.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub repository URL provided."
        )

    job_id = job_manager.create_job("github", payload.url)
    job_dir = job_manager.get_job_dir(job_id)

    try:
        # Download public GitHub repo
        GitHubHandler.download_repo(payload.url, job_dir)

        # Scan files and enforce line limit
        scanner = ProjectScanner(job_dir)
        scan_results = scanner.scan()

        # Run language adapters
        project_analysis = adapter_registry.analyze_project(scan_results)

        job_manager.update_job(
            job_id,
            status="completed",
            stage="analysis",
            stats=project_analysis.model_dump()
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "stage": "analysis",
            "stats": project_analysis.model_dump()
        }

    except IngestionError as exc:
        job_manager.update_job(
            job_id,
            status="failed",
            stage=exc.stage,
            error=exc.message
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "stage": exc.stage,
                "job_id": job_id
            }
        )
    except Exception as exc:
        err_msg = f"Unexpected error during GitHub repository ingestion: {str(exc)}"
        job_manager.update_job(job_id, status="failed", stage="analysis", error=err_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": err_msg, "job_id": job_id}
        )
