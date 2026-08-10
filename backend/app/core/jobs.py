from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4


@dataclass
class Job:
    id: str
    status: str  # processing | completed | failed | cancelled
    result: Any | None = None
    error: str | None = None
    cancel_event: threading.Event | None = None
    created_at: float = 0.0


_JOBS: dict[str, Job] = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_JOBS_LOCK = threading.Lock()
_MAX_RETAINED_JOBS = 100


def _prune_jobs() -> None:
    terminal = sorted(
        (job for job in _JOBS.values() if job.status != "processing"),
        key=lambda job: job.created_at,
    )
    for job in terminal[: max(0, len(_JOBS) - _MAX_RETAINED_JOBS)]:
        _JOBS.pop(job.id, None)


def create_job() -> Job:
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        status="processing",
        cancel_event=threading.Event(),
        created_at=time.monotonic(),
    )
    with _JOBS_LOCK:
        _prune_jobs()
        _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def cancel_job(job_id: str) -> bool:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job or job.status != "processing":
            return False
        if job.cancel_event:
            job.cancel_event.set()
        job.status = "cancelled"
    return True


async def run_job_in_thread(job: Job, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    loop = asyncio.get_running_loop()
    try:
        res = await loop.run_in_executor(
            _EXECUTOR,
            lambda: fn(*args, cancel_event=job.cancel_event, **kwargs),
        )
        if job.status != "cancelled":
            job.result = res
            job.status = "completed"
    except Exception as e:  # noqa: BLE001
        if job.status != "cancelled":
            job.status = "failed"
            job.error = str(e)
