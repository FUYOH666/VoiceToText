"""Single-thread inference worker that owns all model access.

Every job that touches the model (load, transcribe, unload) runs on one
dedicated thread. Admission is a slot handed out as a :class:`Lease`; a lease
can run several jobs one after another (load, then transcribe).

The slot is freed only when the lease is closed *and* its job has really
finished — from the thread's future done-callback, never from the waiting
coroutine. A request that times out (504) therefore keeps the model busy until
MLX returns, so a second inference cannot start on the same model and the idle
unloader cannot drop it mid-inference (it checks ``active_jobs``).

Waiters are served by priority, then arrival: short clips (dictation) go ahead
of long agent files.

All bookkeeping (slot, waiters, ``active_jobs``) happens on the event loop
thread; the worker thread only reports completion via ``call_soon_threadsafe``.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import heapq
import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

PRIORITY_INTERACTIVE = 0
PRIORITY_BATCH = 1
# Clips shorter than this count as dictation and are served first.
INTERACTIVE_MAX_SECONDS = 60.0


def priority_for(audio_seconds: float) -> int:
    return PRIORITY_INTERACTIVE if audio_seconds < INTERACTIVE_MAX_SECONDS else PRIORITY_BATCH


class QueueTimeoutError(Exception):
    """No slot within the queue timeout."""


class JobTimeoutError(Exception):
    """The caller stopped waiting; the job itself keeps running on the worker thread."""


@dataclass
class JobRecord:
    id: int
    kind: str
    priority: int
    audio_seconds: Optional[float] = None
    submitted_at: float = field(default_factory=time.monotonic)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    # Its request stopped waiting (timeout or cancel); the result is only logged.
    abandoned: bool = False


class Lease:
    """Exclusive right to run jobs on the model. Close it when the request is done."""

    def __init__(self, worker: InferenceWorker, priority: int) -> None:
        self._worker = worker
        self.priority = priority
        self._job: Optional[JobRecord] = None
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def run(
        self,
        fn: Callable[..., Any],
        *args: Any,
        timeout: Optional[float] = None,
        kind: str = "job",
        audio_seconds: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        """Run ``fn`` on the worker thread and wait up to ``timeout`` seconds.

        Raises :class:`JobTimeoutError` when the wait runs out; the job keeps the
        slot until it really returns.
        """
        if self._closed:
            raise RuntimeError("lease is closed")
        if self._job is not None:
            raise RuntimeError("a job of this lease is still running")
        return await self._worker._run(
            self, fn, args, kwargs, timeout=timeout, kind=kind, audio_seconds=audio_seconds
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._worker._maybe_release(self)

    async def __aenter__(self) -> Lease:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        self.close()


class InferenceWorker:
    """One thread, one slot, a priority queue of waiters. Create inside the event loop."""

    def __init__(self, thread_name: str = "vtt2-inference") -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix=thread_name
        )
        self._holder: Optional[Lease] = None
        self._waiters: list[tuple[int, int, asyncio.Future]] = []
        self._seq = itertools.count()
        self._job_ids = itertools.count(1)
        self._shut_down = False
        self.active_jobs = 0
        self.current_job: Optional[JobRecord] = None

    # ----- state -----

    @property
    def busy(self) -> bool:
        return self._holder is not None

    @property
    def queued(self) -> int:
        return sum(1 for _p, _s, fut in self._waiters if not fut.done())

    # ----- admission -----

    def try_acquire(self, priority: int = PRIORITY_BATCH) -> Optional[Lease]:
        """A lease now, or None if the slot is held or someone is already waiting."""
        if self._shut_down or self._holder is not None or self.queued:
            return None
        lease = Lease(self, priority)
        self._holder = lease
        return lease

    async def acquire(self, priority: int, timeout: Optional[float]) -> Lease:
        """Wait for the slot up to ``timeout`` seconds (None: forever)."""
        if self._shut_down:
            raise QueueTimeoutError("worker is shut down")
        lease = self.try_acquire(priority)
        if lease is not None:
            return lease
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        heapq.heappush(self._waiters, (priority, next(self._seq), fut))
        try:
            # asyncio.wait never cancels fut, so a hand-off cannot be lost to a timeout race.
            await asyncio.wait({fut}, timeout=None if timeout is None else max(0.0, timeout))
        except BaseException:
            self._leave_queue(fut)
            raise
        if fut.done() and not fut.cancelled():
            return fut.result()
        self._leave_queue(fut)
        raise QueueTimeoutError(f"no free slot within {timeout}s")

    def _leave_queue(self, fut: asyncio.Future) -> None:
        if fut.done() and not fut.cancelled():
            fut.result().close()  # slot was handed to us as we left: pass it on
        else:
            fut.cancel()
        self._waiters = [w for w in self._waiters if not w[2].done()]
        heapq.heapify(self._waiters)

    def _maybe_release(self, lease: Lease) -> None:
        if not lease.closed or lease._job is not None or self._holder is not lease:
            return
        self._holder = None
        while self._waiters:
            priority, _seq, fut = heapq.heappop(self._waiters)
            if fut.done():
                continue
            nxt = Lease(self, priority)
            self._holder = nxt
            fut.set_result(nxt)
            return

    # ----- jobs -----

    async def _run(
        self,
        lease: Lease,
        fn: Callable[..., Any],
        args: tuple,
        kwargs: dict,
        *,
        timeout: Optional[float],
        kind: str,
        audio_seconds: Optional[float],
    ) -> Any:
        loop = asyncio.get_running_loop()
        job = JobRecord(
            id=next(self._job_ids),
            kind=kind,
            priority=lease.priority,
            audio_seconds=audio_seconds,
        )
        done: asyncio.Future = loop.create_future()

        def call() -> Any:
            job.started_at = time.monotonic()
            return fn(*args, **kwargs)

        def on_thread_done(cf: concurrent.futures.Future) -> None:
            try:
                loop.call_soon_threadsafe(self._job_finished, lease, job, cf, done)
            except RuntimeError:
                pass  # event loop already closed: the process is exiting

        cf = self._executor.submit(call)
        lease._job = job
        self.active_jobs += 1
        self.current_job = job
        cf.add_done_callback(on_thread_done)
        try:
            await asyncio.wait({done}, timeout=timeout)
        except BaseException:
            job.abandoned = True
            raise
        if not done.done():
            job.abandoned = True
            raise JobTimeoutError(f"{kind} job #{job.id} still running after {timeout}s")
        return done.result()

    def _job_finished(
        self,
        lease: Lease,
        job: JobRecord,
        cf: concurrent.futures.Future,
        done: asyncio.Future,
    ) -> None:
        job.finished_at = time.monotonic()
        self.active_jobs -= 1
        if self.current_job is job:
            self.current_job = None
        lease._job = None
        exc = None if cf.cancelled() else cf.exception()
        if job.abandoned:
            logger.warning(
                "STT: %s job #%d finished %.1fs after submit; its request had stopped waiting%s",
                job.kind,
                job.id,
                job.finished_at - job.submitted_at,
                f" (error: {exc!r})" if exc else "",
            )
        elif not done.done():
            if cf.cancelled():
                done.cancel()
            elif exc is not None:
                done.set_exception(exc)
            else:
                done.set_result(cf.result())
        self._maybe_release(lease)

    def shutdown(self) -> None:
        """Refuse new work and wake waiters. A running job is left to finish."""
        self._shut_down = True
        for _p, _s, fut in self._waiters:
            if not fut.done():
                fut.cancel()
        self._waiters.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)
