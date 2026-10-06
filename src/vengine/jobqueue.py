"""Single-writer background import queue with restart recovery."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from .jobs import run_job
from .models import ImportJob
from .store import Store


class JobQueue:
    def __init__(self, store: Store):
        self.store = store
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vengine-import")
        self._futures: dict[str, Future[ImportJob]] = {}
        self._lock = Lock()

    def submit(self, job_id: str) -> ImportJob:
        job = self.store.job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.stage == "review_ready":
            return job
        with self._lock:
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                return job
            if job.stage in {"failed", "cancelled"}:
                job = job.model_copy(update={"stage": "queued", "error": None})
                self.store.save_job(job)
            self._futures[job_id] = self._executor.submit(run_job, self.store, job_id)
        return job

    def cancel(self, job_id: str) -> ImportJob:
        job = self.store.job(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.stage in {"review_ready", "failed", "cancelled"}:
            return job
        job = job.model_copy(update={"stage": "cancelled"})
        self.store.save_job(job)
        with self._lock:
            future = self._futures.get(job_id)
            if future:
                future.cancel()
        return job

    def recover(self) -> None:
        for job in self.store.jobs():
            if job.stage in {"queued", "extracting", "generating"}:
                self.submit(job.id)

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
