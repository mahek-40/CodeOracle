import os
import json
import shutil
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.config import settings

DEFAULT_TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tmp", "jobs"))
TEMP_BASE_DIR = os.path.abspath(settings.TEMP_DIR) if settings.TEMP_DIR else DEFAULT_TEMP_DIR


class JobManager:
    """Manages temporary job workspace directories and in-memory + on-disk job state persistence."""

    def __init__(self, base_dir: str = TEMP_BASE_DIR):
        self.base_dir = base_dir
        self._jobs: Dict[str, Dict[str, Any]] = {}

        os.makedirs(self.base_dir, exist_ok=True)

    def _meta_path(self, job_id: str) -> str:
        return os.path.join(self.base_dir, job_id, "job_meta.json")

    def _save_job_to_disk(self, job_data: Dict[str, Any]):
        job_id = job_data.get("job_id")
        if not job_id:
            return
        meta_file = self._meta_path(job_id)
        try:
            os.makedirs(os.path.dirname(meta_file), exist_ok=True)
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(job_data, f, indent=2)
        except Exception:
            pass

    def _load_job_from_disk(self, job_id: str) -> Optional[Dict[str, Any]]:
        meta_file = self._meta_path(job_id)
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    self._jobs[job_id] = job_data
                    return job_data
            except Exception:
                pass
        return None

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
        self._save_job_to_disk(job_data)
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
        job = self.get_job(job_id)
        if not job:
            return None

        job["status"] = status
        job["stage"] = stage
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        if stats is not None:
            job["stats"] = stats
        if error is not None:
            job["error"] = error
        if stage_error is not None:
            job["stage_error"] = stage_error

        self._jobs[job_id] = job
        self._save_job_to_disk(job)
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id in self._jobs:
            return self._jobs[job_id]
        return self._load_job_from_disk(job_id)

    def save_job_field(self, job_id: str, field_name: str, value: Any):
        """Persists a specialized result field (e.g. test_generation, test_execution) to job state and disk."""
        job = self.get_job(job_id)
        if job:
            job[field_name] = value
            self._jobs[job_id] = job
            self._save_job_to_disk(job)

    def delete_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job:
            job_dir = job.get("job_dir") or os.path.join(self.base_dir, job_id)
            if job_dir and os.path.exists(job_dir):
                try:
                    shutil.rmtree(job_dir, ignore_errors=True)
                except Exception:
                    pass
            if job_id in self._jobs:
                del self._jobs[job_id]
            return True
        return False


job_manager = JobManager()
