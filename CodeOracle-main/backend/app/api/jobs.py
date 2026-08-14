from fastapi import APIRouter, HTTPException, status
from app.jobs.manager import job_manager
from app.graph.builder import graph_builder
from app.analyzers.base.schema import ProjectAnalysis

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Returns state, stage, statistics, and any stage errors for a given job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    client_response = {k: v for k, v in job.items() if k != "job_dir"}
    return client_response


@router.get("/{job_id}/graph")
async def get_job_graph(job_id: str):
    """
    Builds and returns the dependency graph for a completed job.
    Graph is derived from the normalized ProjectAnalysis produced in Phase 2.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not yet completed (status: {job.get('status')})."
        )

    stats = job.get("stats")
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has no analysis stats yet."
        )

    try:
        project_analysis = ProjectAnalysis.model_validate(stats)
        graph = graph_builder.build(project_analysis)
        return graph.model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dependency graph: {str(exc)}"
        )


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Cancels job and cleans up temporary workspace files."""
    deleted = job_manager.delete_job(job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    return {"message": f"Job '{job_id}' and associated temporary files deleted successfully."}
