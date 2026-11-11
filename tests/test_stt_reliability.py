"""STT server concurrency, timeouts, limits and the error contract (docs/STT_API.md).

A slow fake engine blocks inside ``transcribe_detailed`` until the test lets it
go, so a request can time out (504) while its inference is still running.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.limits import BodySizeLimitMiddleware
from server.worker import (
    PRIORITY_BATCH,
    PRIORITY_INTERACTIVE,
    InferenceWorker,
    JobTimeoutError,
    QueueTimeoutError,
    priority_for,
)
from stt_server import _idle_unload_once, create_app, state

from .test_stt_server import _detailed_payload, _minimal_config, _mock_engine, _wav_bytes

URL = "/v1/audio/transcriptions"


class SlowEngine:
    """Blocks in transcribe_detailed until ``release`` is set. Counts overlap."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self._mu = threading.Lock()

    def transcribe(self, audio):
        return ""

    def transcribe_detailed(self, audio, **kwargs):
        with self._mu:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        self.started.set()
        try:
            if not self.release.wait(10):
                raise RuntimeError("test never released the slow engine")
            return _detailed_payload("медленно")
        finally:
            with self._mu:
                self.active -= 1


def _stt_server(**overrides) -> dict:
    base = {
        "host": "127.0.0.1",
        "port": 8765,
        "max_upload_mb": 1,
        "request_timeout_seconds": 60,
        "engine": "mlx_whisper",
        "preload_on_start": True,
        "idle_unload_seconds": 0,
        "queue_timeout_seconds": 0.2,
    }
    base.update(overrides)
    return base


@contextmanager
def _client(engine, *, request_timeout: float | None = None, **stt_overrides):
    config = _minimal_config(stt_server=_stt_server(**stt_overrides))
    with ExitStack() as stack:
        stack.enter_context(patch("stt_server.TranscriptionEngineWrapper", return_value=engine))
        stack.enter_context(patch("stt_server._warmup", return_value=None))
        if request_timeout is not None:
            # Config enforces >= 30 s; a short timeout makes a 504 take a fraction of a second.
            stack.enter_context(patch("stt_server._request_timeout", return_value=request_timeout))
        client = stack.enter_context(TestClient(create_app(config)))
        try:
            yield client
        finally:
            release = getattr(engine, "release", None)
            if release is not None:
                release.set()
            _wait_until(lambda: client.get("/healthz").json()["active_jobs"] == 0)


@pytest.fixture
def ready_app():
    engine = _mock_engine()
    with _client(engine) as client:
        yield client, engine


def _post(client, seconds: float = 0.2, **data):
    return client.post(
        URL, files={"file": ("a.wav", _wav_bytes(seconds), "audio/wav")}, data=data
    )


def _wait_until(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.01)


def _assert_error(response, status: int, code: str, err_type: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error", "detail"}
    error = body["error"]
    assert error["code"] == code
    assert error["type"] == err_type
    assert error["param"] is None
    assert isinstance(error["message"], str) and error["message"]
    assert body["detail"] == error["message"]
    return error


class TestTimeoutKeepsModelBusy:
    def test_504_then_429_while_first_inference_still_runs(self):
        engine = SlowEngine()
        with _client(engine, request_timeout=0.3) as client:
            r1 = _post(client)
            _assert_error(r1, 504, "transcription_timeout", "server_error")
            assert engine.active == 1, "inference must still be running after the 504"
            health = client.get("/healthz").json()
            assert health["active_jobs"] == 1

            r2 = _post(client)
            _assert_error(r2, 429, "busy", "rate_limit_error")
            assert r2.headers["Retry-After"] == "5"
            assert engine.calls == 1, "the second request must not reach the model"

            engine.release.set()
            _wait_until(lambda: client.get("/healthz").json()["active_jobs"] == 0)

            r3 = _post(client)
            assert r3.status_code == 200
            assert r3.json()["text"] == "медленно"
            assert engine.max_active == 1

    def test_idle_unloader_skips_while_job_active(self):
        engine = SlowEngine()
        with _client(engine, request_timeout=0.3, idle_unload_seconds=1) as client:
            assert _post(client).status_code == 504
            state.last_used_at = time.time() - 3600

            with patch("stt_server._release_mlx_cache") as release_cache:
                assert client.portal.call(_idle_unload_once) is False
                assert state.ready is True
                assert state.engine is engine
                release_cache.assert_not_called()

                engine.release.set()
                _wait_until(lambda: client.get("/healthz").json()["active_jobs"] == 0)
                state.last_used_at = time.time() - 3600
                assert client.portal.call(_idle_unload_once) is True
            assert state.ready is False
            assert client.get("/readyz").status_code == 503


class TestModelLoad:
    def test_permanent_load_failure_is_500_not_503(self):
        config = _minimal_config(
            stt_server=_stt_server(preload_on_start=False, idle_unload_seconds=900)
        )
        with patch(
            "stt_server.TranscriptionEngineWrapper",
            side_effect=RuntimeError("weights missing"),
        ):
            with TestClient(create_app(config)) as client:
                r = _post(client)
                error = _assert_error(r, 500, "model_load_failed", "server_error")
                assert "weights missing" in error["message"]
                assert "Retry-After" not in r.headers

                health = client.get("/healthz").json()
                assert health["ready"] is False
                assert health["loading"] is False
                assert "weights missing" in health["last_error"]
                assert health["active_jobs"] == 0

                # Not stuck: the next request tries the load again and fails the same way.
                _assert_error(_post(client), 500, "model_load_failed", "server_error")

    def test_slow_load_is_503_model_loading_and_queue_sees_loading(self):
        config = _minimal_config(
            stt_server=_stt_server(preload_on_start=False, idle_unload_seconds=900)
        )
        gate = threading.Event()

        def slow_warmup(*_a, **_k):
            assert gate.wait(10)

        with ExitStack() as stack:
            stack.enter_context(
                patch("stt_server.TranscriptionEngineWrapper", return_value=_mock_engine("ok"))
            )
            stack.enter_context(patch("stt_server._warmup", side_effect=slow_warmup))
            stack.enter_context(patch("stt_server._request_timeout", return_value=0.3))
            client = stack.enter_context(TestClient(create_app(config)))
            try:
                r1 = _post(client)
                _assert_error(r1, 503, "model_loading", "server_error")
                assert r1.headers["Retry-After"] == "2"
                assert client.get("/healthz").json()["loading"] is True

                r2 = _post(client)  # waits in the queue behind the load
                _assert_error(r2, 503, "model_loading", "server_error")
            finally:
                gate.set()
            _wait_until(lambda: client.get("/healthz").json()["ready"])
            r3 = _post(client)
            assert r3.status_code == 200
            assert r3.json()["text"] == "ok"


class TestLimits:
    def test_oversized_content_length_rejected_before_body_is_read(self):
        app = create_app(_minimal_config())  # max_upload_mb=1
        reads: list[int] = []
        sent: list[dict] = []

        async def receive():
            reads.append(1)
            raise AssertionError("the body must not be read")

        async def send(message):
            sent.append(message)

        scope = _http_scope(
            [
                (b"content-type", b"multipart/form-data; boundary=x"),
                (b"content-length", str(50 * 1024 * 1024).encode()),
            ]
        )
        asyncio.run(app(scope, receive, send))

        assert reads == []
        assert sent[0]["type"] == "http.response.start"
        assert sent[0]["status"] == 413
        body = json.loads(sent[1]["body"])
        assert body["error"]["code"] == "file_too_large"
        assert body["error"]["type"] == "invalid_request_error"

    def test_streamed_body_cut_off_at_limit(self):
        # No Content-Length (chunked upload): bytes are counted while they stream.
        engine = _mock_engine()
        chunk = 64 * 1024
        total_chunks = 48  # 3 MB against a 1 MB (+64 KB) limit
        reads = {"n": 0}
        sent: list[dict] = []

        async def receive():
            reads["n"] += 1
            if reads["n"] == 1:
                return {
                    "type": "http.request",
                    "body": b"--x\r\nContent-Disposition: form-data; name=\"file\"; "
                    b"filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n",
                    "more_body": True,
                }
            more = reads["n"] <= total_chunks
            return {"type": "http.request", "body": b"\0" * chunk, "more_body": more}

        async def send(message):
            sent.append(message)

        with patch("stt_server.TranscriptionEngineWrapper", return_value=engine):
            app = create_app(_minimal_config())
            scope = _http_scope([(b"content-type", b"multipart/form-data; boundary=x")])
            asyncio.run(app(scope, receive, send))

        starts = [m for m in sent if m["type"] == "http.response.start"]
        assert [m["status"] for m in starts] == [413]
        body = json.loads(
            b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
        )
        assert body["error"]["code"] == "file_too_large"
        limit_chunks = (1024 * 1024 + 64 * 1024) // chunk
        assert reads["n"] <= limit_chunks + 2, "reading must stop at the limit"
        engine.transcribe_detailed.assert_not_called()

    def test_declared_size_over_limit_through_client(self, ready_app):
        client, engine = ready_app
        r = client.post(URL, files={"file": ("big.wav", b"RIFF" + b"x" * (2 * 1024 * 1024))})
        _assert_error(r, 413, "file_too_large", "invalid_request_error")
        engine.transcribe_detailed.assert_not_called()

    def test_audio_longer_than_max_audio_seconds_is_413(self):
        engine = _mock_engine()
        with _client(engine, max_audio_seconds=1) as client:
            r = _post(client, seconds=2.0)
            error = _assert_error(r, 413, "audio_too_long", "invalid_request_error")
            assert "max_audio_seconds" in error["message"]
            engine.transcribe_detailed.assert_not_called()
            assert _post(client, seconds=0.5).status_code == 200


class TestErrorShape:
    def test_invalid_audio(self, ready_app):
        client, _ = ready_app
        r = client.post(URL, files={"file": ("bad.wav", b"not-audio", "audio/wav")})
        _assert_error(r, 400, "invalid_audio", "invalid_request_error")

    def test_empty_file(self, ready_app):
        client, _ = ready_app
        r = client.post(URL, files={"file": ("empty.wav", b"", "audio/wav")})
        _assert_error(r, 400, "invalid_audio", "invalid_request_error")

    def test_unsupported_language(self, ready_app):
        client, _ = ready_app
        r = _post(client, language="Thai")
        _assert_error(r, 400, "unsupported_language", "invalid_request_error")

    def test_bad_response_format(self, ready_app):
        client, _ = ready_app
        r = _post(client, response_format="srt")
        _assert_error(r, 400, "invalid_request", "invalid_request_error")

    def test_missing_file_is_400_not_422(self, ready_app):
        client, _ = ready_app
        r = client.post(URL, data={"language": "ru"})
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "invalid_request"
        assert "file" in body["error"]["message"]
        assert isinstance(body["detail"], list)  # FastAPI's own validation list, as before

    def test_engine_failure_is_500_transcription_failed(self, ready_app):
        client, engine = ready_app
        engine.transcribe_detailed.side_effect = RuntimeError("metal exploded")
        r = _post(client)
        error = _assert_error(r, 500, "transcription_failed", "server_error")
        assert "metal" not in error["message"]  # internals stay in the log
        engine.transcribe_detailed.side_effect = None
        assert _post(client).status_code == 200

    def test_unknown_path_is_shaped_404(self, ready_app):
        client, _ = ready_app
        r = client.get("/nope")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "not_found"

    def test_healthz_reports_queue_fields(self, ready_app):
        client, _ = ready_app
        body = client.get("/healthz").json()
        for key in ("ready", "loading", "last_error", "active_jobs", "queued"):
            assert key in body
        assert body["last_error"] is None
        assert body["active_jobs"] == 0


class TestInferenceWorker:
    def test_timeout_keeps_slot_until_job_returns(self):
        async def scenario():
            worker = InferenceWorker()
            gate = threading.Event()
            lease = await worker.acquire(PRIORITY_INTERACTIVE, timeout=None)
            with pytest.raises(JobTimeoutError):
                await lease.run(gate.wait, 5, timeout=0.05)
            lease.close()
            assert worker.busy and worker.active_jobs == 1
            assert worker.try_acquire() is None
            with pytest.raises(QueueTimeoutError):
                await worker.acquire(PRIORITY_INTERACTIVE, timeout=0.05)
            gate.set()
            for _ in range(500):
                if worker.active_jobs == 0:
                    break
                await asyncio.sleep(0.01)
            assert worker.active_jobs == 0 and not worker.busy
            nxt = worker.try_acquire()
            assert nxt is not None
            nxt.close()
            worker.shutdown()

        asyncio.run(scenario())

    def test_all_jobs_run_on_one_thread(self):
        async def scenario():
            worker = InferenceWorker()
            names = set()
            for _ in range(3):
                async with await worker.acquire(PRIORITY_BATCH, timeout=1) as lease:
                    names.add(await lease.run(lambda: threading.current_thread().name))
            worker.shutdown()
            return names

        names = asyncio.run(scenario())
        assert len(names) == 1
        assert next(iter(names)).startswith("vtt2-inference")

    def test_dictation_goes_ahead_of_queued_long_job(self):
        async def scenario():
            worker = InferenceWorker()
            gate = threading.Event()
            order: list[str] = []
            first = await worker.acquire(PRIORITY_BATCH, timeout=None)
            running = asyncio.create_task(first.run(gate.wait, 5))
            await asyncio.sleep(0)

            async def waiter(name: str, priority: int) -> None:
                lease = await worker.acquire(priority, timeout=5)
                order.append(name)
                lease.close()

            long_job = asyncio.create_task(waiter("agent file", PRIORITY_BATCH))
            await asyncio.sleep(0)
            dictation = asyncio.create_task(waiter("dictation", PRIORITY_INTERACTIVE))
            await asyncio.sleep(0)
            assert worker.queued == 2
            first.close()
            await asyncio.sleep(0.05)
            assert order == [], "no hand-off while the job still runs"
            gate.set()
            await running
            await asyncio.gather(long_job, dictation)
            worker.shutdown()
            return order

        assert asyncio.run(scenario()) == ["dictation", "agent file"]

    def test_job_error_reaches_caller_and_frees_slot(self):
        async def scenario():
            worker = InferenceWorker()

            def boom():
                raise ValueError("bad input")

            async with await worker.acquire(PRIORITY_INTERACTIVE, timeout=1) as lease:
                with pytest.raises(ValueError, match="bad input"):
                    await lease.run(boom)
            assert not worker.busy and worker.active_jobs == 0
            worker.shutdown()

        asyncio.run(scenario())

    def test_priority_threshold(self):
        assert priority_for(5.0) == PRIORITY_INTERACTIVE
        assert priority_for(59.9) == PRIORITY_INTERACTIVE
        assert priority_for(60.0) == PRIORITY_BATCH


class TestBodySizeLimitMiddleware:
    def test_small_body_passes_through(self):
        seen: list[bytes] = []

        async def app(scope, receive, send):
            message = await receive()
            seen.append(message["body"])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw = BodySizeLimitMiddleware(app, max_bytes=10, message="too big")
        sent: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b"12345", "more_body": False}

        async def send(message):
            sent.append(message)

        asyncio.run(mw(_http_scope([(b"content-length", b"5")]), receive, send))
        assert seen == [b"12345"]
        assert sent[0]["status"] == 200


def _http_scope(headers: list[tuple[bytes, bytes]]) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": URL,
        "raw_path": URL.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8765),
    }
