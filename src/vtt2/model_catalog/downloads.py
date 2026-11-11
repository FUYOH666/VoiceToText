"""Background model downloads with progress.

A download runs ``huggingface_hub.snapshot_download`` on its own thread, never
on the inference worker, so dictation keeps working while a model downloads.
Progress is measured from the bytes in the repo's cache folder (including
``.incomplete`` files), which works no matter how the hub library reports it.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from model_catalog.registry import ALLOW_PATTERNS, ModelSpec, is_installed

logger = logging.getLogger(__name__)


def snapshot_download(**kwargs):  # pragma: no cover - thin seam for tests
    from huggingface_hub import snapshot_download as hub_download

    return hub_download(**kwargs)


def hub_total_bytes(spec: ModelSpec) -> Optional[int]:
    """Exact download size from the hub, counting only files the family needs."""
    try:
        from fnmatch import fnmatch

        from huggingface_hub import HfApi

        info = HfApi().model_info(spec.repo, files_metadata=True)
        patterns = ALLOW_PATTERNS[spec.family]
        return sum(
            (s.size or 0)
            for s in info.siblings
            if any(fnmatch(s.rfilename, p) for p in patterns)
        )
    except Exception as exc:
        logger.debug("size lookup for %s failed: %s", spec.repo, exc)
        return None


def repo_cache_dir(repo: str) -> Path:
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE) / f"models--{repo.replace('/', '--')}"


def cached_bytes(repo: str) -> int:
    blobs = repo_cache_dir(repo) / "blobs"
    if not blobs.is_dir():
        return 0
    total = 0
    for item in blobs.iterdir():
        try:
            total += item.stat().st_size
        except OSError:
            pass
    return total


@dataclass
class DownloadJob:
    model_id: str
    repo: str
    state: str = "queued"  # queued | downloading | done | error
    bytes_total: Optional[int] = None
    bytes_at_start: int = 0
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    thread: Optional[threading.Thread] = field(default=None, repr=False)

    def progress(self) -> dict:
        done = max(0, cached_bytes(self.repo) - self.bytes_at_start)
        total = self.bytes_total
        if self.state == "done":
            fraction = 1.0
        elif total:
            fraction = min(done / total, 0.99)
        else:
            fraction = None
        return {
            "model": self.model_id,
            "state": self.state,
            "bytes_done": total if self.state == "done" and total else done,
            "bytes_total": total,
            "progress": fraction,
            "error": self.error,
        }


class DownloadManager:
    """One download per model at a time; finished jobs stay queryable."""

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def start(self, spec: ModelSpec) -> DownloadJob:
        with self._lock:
            job = self._jobs.get(spec.id)
            if job is not None and job.state in ("queued", "downloading"):
                return job
            job = DownloadJob(model_id=spec.id, repo=spec.repo)
            if is_installed(spec):
                job.state = "done"
                job.finished_at = time.time()
                self._jobs[spec.id] = job
                return job
            job.bytes_at_start = cached_bytes(spec.repo)
            job.thread = threading.Thread(
                target=self._run, args=(job, spec), name=f"download-{spec.id}", daemon=True
            )
            self._jobs[spec.id] = job
        job.thread.start()
        return job

    def get(self, model_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self._jobs.get(model_id)

    def is_running(self, model_id: str) -> bool:
        job = self.get(model_id)
        return job is not None and job.state in ("queued", "downloading")

    def _run(self, job: DownloadJob, spec: ModelSpec) -> None:
        job.state = "downloading"
        total = hub_total_bytes(spec)
        if total is None and spec.download_gb:
            total = int(spec.download_gb * 1e9)
        job.bytes_total = total
        logger.info("Model download started: %s (%s)", spec.id, spec.repo)
        try:
            snapshot_download(repo_id=spec.repo, allow_patterns=ALLOW_PATTERNS[spec.family])
        except Exception as exc:
            job.state = "error"
            job.error = str(exc)[:300]
            logger.error("Model download failed: %s: %s", spec.id, exc)
        else:
            job.state = "done"
            logger.info("Model download finished: %s", spec.id)
        finally:
            job.finished_at = time.time()
