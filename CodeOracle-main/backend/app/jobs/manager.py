import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.config import settings

DEFAULT_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tmp", "jobs"))
TEMP_BASE_DIR = os.path.abspath(settings.TEMP_DIR) if settings.TEMP_DIR else DEFAULT_TEMP_DIR


class JobManager:
    """Manages temporary job workspace directories and in-memory job state metadata."""

    def __init__(self, base_dir: str = TEMP_BASE_DIR):
        self.base_dir = base_dir
        self._jobs: Dict[str, Dict[str, Any]] = {}

        os.makedirs(self.base_dir, exist_ok=True)

    def create_job(self, source_type: str, source_info: str) -> str:
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(self.base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        job_data = {
            "job_id": job_id,
            "status": "processing",
            "stage": "ingestion",
            "source_type": source_type,
            "source_info": source_info,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stats": None,
            "error": None,
            "stage_error": None,
            "job_dir": job_dir
        }

        self._jobs[job_id] = job_data
        return job_id

    def get_job_dir(self, job_id: str) -> str:
        job_dir = os.path.join(self.base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    def update_job(
        self,
        job_id: str,
        status: str,
        stage: str,
        stats: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        stage_error: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if job_id not in self._jobs:
            return None

        job = self._jobs[job_id]
        job["status"] = status
        job["stage"] = stage
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        if stats is not None:
            job["stats"] = stats
        if error is not None:
            job["error"] = error
        if stage_error is not None:
            job["stage_error"] = stage_error

        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            job_dir = self._jobs[job_id].get("job_dir")
            if job_dir and os.path.exists(job_dir):
                try:
                    shutil.rmtree(job_dir, ignore_errors=True)
                except Exception:
                    pass
            del self._jobs[job_id]
            return True
        return False


job_manager = JobManager()
