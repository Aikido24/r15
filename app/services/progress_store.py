from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.models.responses import AnalyzeResponse, JobProgressResponse, JobStatus

_UNSET = object()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_progress(progress_percent: int) -> int:
    return max(0, min(100, progress_percent))


class JobProgressStore:
    """Thread-safe in-memory store for analysis job progress."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobProgressResponse] = {}
        self._lock = Lock()

    def create_job(
        self,
        *,
        job_id: str | None = None,
        status: JobStatus = "queued",
        stage: str = "queued",
        progress_percent: int = 0,
        message: str = "",
    ) -> JobProgressResponse:
        now = _utc_now()
        snapshot = JobProgressResponse(
            job_id=job_id or uuid4().hex,
            status=status,
            stage=stage,
            progress_percent=_clamp_progress(progress_percent),
            message=message,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[snapshot.job_id] = snapshot

        return snapshot.model_copy(deep=True)

    def get_job(self, job_id: str) -> JobProgressResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            return job.model_copy(deep=True)

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        stage: str | None = None,
        progress_percent: int | None = None,
        message: str | None = None,
        current_page: int | None | object = _UNSET,
        total_pages: int | None | object = _UNSET,
        result: AnalyzeResponse | None | object = _UNSET,
        error: str | None | object = _UNSET,
    ) -> JobProgressResponse:
        with self._lock:
            current_job = self._jobs.get(job_id)
            if current_job is None:
                raise KeyError(f"Job '{job_id}' does not exist.")

            updates: dict[str, object] = {"updated_at": _utc_now()}
            if status is not None:
                updates["status"] = status
            if stage is not None:
                updates["stage"] = stage
            if progress_percent is not None:
                updates["progress_percent"] = _clamp_progress(progress_percent)
            if message is not None:
                updates["message"] = message
            if current_page is not _UNSET:
                updates["current_page"] = current_page
            if total_pages is not _UNSET:
                updates["total_pages"] = total_pages
            if result is not _UNSET:
                updates["result"] = result
            if error is not _UNSET:
                updates["error"] = error

            updated_job = current_job.model_copy(update=updates, deep=True)
            self._jobs[job_id] = updated_job
            return updated_job.model_copy(deep=True)

    def complete_job(
        self,
        job_id: str,
        *,
        result: AnalyzeResponse,
        message: str = "Analisis completado.",
    ) -> JobProgressResponse:
        return self.update_job(
            job_id,
            status="completed",
            stage="completed",
            progress_percent=100,
            message=message,
            result=result,
            error=None,
        )

    def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        message: str = "El analisis fallo.",
    ) -> JobProgressResponse:
        return self.update_job(
            job_id,
            status="failed",
            stage="failed",
            message=message,
            error=error,
            result=None,
        )

    def delete_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def list_jobs(self) -> list[JobProgressResponse]:
        with self._lock:
            return [job.model_copy(deep=True) for job in self._jobs.values()]


job_progress_store = JobProgressStore()
