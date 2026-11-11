"""
Local OpenAI-compatible STT HTTP API.

Owns one ASR model in one process (default qwen3_asr; Whisper is a menu switch).
Menubar and agents are clients.
Bind: loopback only. Concurrency: 1 — every model call runs on one worker
thread (server.worker); errors follow the contract in docs/STT_API.md.

Profiles:
- preload_on_start=true, idle_unload_seconds=0 → resident (config.resident.yaml)
- preload_on_start=false, idle_unload_seconds>0 → idle unload (default config.yaml)
"""
from __future__ import annotations

import asyncio
import gc
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from audio.decode import AudioDecodeError, decode_audio_bytes
from audio.processor import AudioProcessor
from config.loader import Config
from server import errors as err
from server.errors import APIError, install_error_handlers
from server.limits import BodySizeLimitMiddleware
from server.models_api import ModelHost, register_model_routes
from server.worker import (
    PRIORITY_INTERACTIVE,
    InferenceWorker,
    JobTimeoutError,
    Lease,
    QueueTimeoutError,
    priority_for,
)
from transcription.engine import TranscriptionEngineWrapper
from transcription.request_language import RejectedLanguage, resolve_request_language

logger = logging.getLogger(__name__)

PROMPT_MAX_CHARS = 1000
# Multipart boundaries and form fields on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 64 * 1024
IDLE_CHECK_INTERVAL_SECONDS = 15


class STTState:
    """Mutable server state (model readiness + engine)."""

    def __init__(self) -> None:
        self.ready: bool = False
        self.loading: bool = False
        self.warmup_error: Optional[str] = None
        self.config: Optional[Config] = None
        self.engine: Optional[TranscriptionEngineWrapper] = None
        self.processor: Optional[AudioProcessor] = None
        self.worker: Optional[InferenceWorker] = None
        self.model_name: str = ""
        self.last_used_at: float = 0.0
        self.idle_task: Optional[asyncio.Task] = None


state = STTState()


def _server_engine_config(config: Config) -> Config:
    """Clone-like override: transcription.engine = stt_server.engine for in-process load."""
    data = config.model_dump()
    data["transcription"]["engine"] = config.stt_server.engine
    return Config(**data)


# Engines whose models produce the subtitle/sound-event hallucinations that
# text.whisper_artifacts targets. Other engines (Qwen3-ASR) are never filtered:
# the phrase list would only delete real words from their output.
WHISPER_FAMILY_ENGINES = frozenset({"mlx_whisper", "whisper_cpp"})


def _artifact_filter_applies(config: Config) -> bool:
    return (
        config.text_processing.strip_whisper_tail_artifacts
        and config.stt_server.engine in WHISPER_FAMILY_ENGINES
        and bool(config.text_processing.whisper_artifact_languages)
    )


def _strip_artifacts(text: str, config: Config) -> str:
    from text.whisper_artifacts import strip_trailing_whisper_artifacts

    langs = frozenset(config.text_processing.whisper_artifact_languages)
    if not langs:
        return text
    cleaned, stripped = strip_trailing_whisper_artifacts(text, languages=langs)
    if stripped:
        logger.info(
            "STT: удалён хвостовой артефакт Whisper (−%d символов)",
            len(text) - len(cleaned),
        )
    return cleaned


def _strip_artifacts_payload(payload: dict, config: Config) -> dict:
    """Strip known Whisper hallucinations per segment (Whisper engines only).

    ``text`` is rebuilt from segments only when a segment actually changed, so
    the engine's own text (spacing, CJK/Thai joins) is kept otherwise.
    """
    if not _artifact_filter_applies(config):
        return payload
    segments = list(payload.get("segments") or [])
    if segments:
        cleaned = []
        changed = False
        for seg in segments:
            item = dict(seg)
            original = item.get("text") or ""
            item["text"] = _strip_artifacts(original, config)
            if item["text"] != original:
                changed = True
            if item["text"].strip():
                cleaned.append(item)
        if changed:
            payload["segments"] = cleaned
            payload["text"] = " ".join(
                (s.get("text") or "").strip()
                for s in cleaned
                if (s.get("text") or "").strip()
            ).strip()
    else:
        payload["text"] = _strip_artifacts(payload.get("text") or "", config)
    return payload


def _want_word_timestamps(*parts: Optional[str]) -> bool:
    blob = " ".join(p for p in parts if p)
    return "word" in blob.lower()


def _warmup(engine: TranscriptionEngineWrapper, sample_rate: int) -> None:
    """Force model load with short silence (not meant to produce text)."""
    silence = np.zeros(int(sample_rate * 0.5), dtype=np.float32)
    try:
        engine.transcribe(silence)
    except Exception as e:
        msg = str(e).lower()
        if "не установлен" in msg or "not found" in msg or "не найден" in msg:
            raise
        logger.warning("STT warmup returned error (model likely loaded): %s", e)


def _release_mlx_cache() -> None:
    """Best-effort Metal/MLX buffer release after model drop."""
    gc.collect()
    try:
        import mlx.core as mx

        if hasattr(mx, "clear_cache"):
            mx.clear_cache()
            logger.info("STT: mlx.core.clear_cache() done")
    except Exception as e:
        logger.debug("STT: mlx clear_cache skipped: %s", e)


def _configured_model_name(config: Config) -> str:
    """Checkpoint id the process will load. HTTP ``model=`` does not change this."""
    if config.stt_server.engine == "qwen3_asr" and config.transcription.qwen3_asr:
        return config.transcription.qwen3_asr.model_name
    if config.transcription.mlx_whisper:
        return config.transcription.mlx_whisper.model_name
    return config.stt_server.engine


def _profile_language(config: Config) -> Optional[str]:
    """Language used when the request omits the field. Depends on the loaded engine."""
    if config.stt_server.engine == "qwen3_asr" and config.transcription.qwen3_asr:
        return config.transcription.qwen3_asr.language
    if config.transcription.mlx_whisper is not None:
        return config.transcription.mlx_whisper.language
    return None


def _load_model_sync(config: Config) -> None:
    """Load engine + warmup (blocking; call via to_thread)."""
    eng_config = _server_engine_config(config)
    engine = TranscriptionEngineWrapper(eng_config)
    processor = AudioProcessor()
    state.model_name = _configured_model_name(config)
    _warmup(engine, eng_config.audio.sample_rate)
    state.engine = engine
    state.processor = processor
    state.ready = True
    state.warmup_error = None
    state.last_used_at = time.time()
    logger.info("STT model loaded: %s", state.model_name)


def _unload_model_sync() -> None:
    """Drop engine references and ask MLX to free GPU cache."""
    state.ready = False
    engine = state.engine
    state.engine = None
    state.processor = None
    inner = getattr(engine, "engine", None)
    release = getattr(inner, "release", None)
    if callable(release):
        try:
            release()
        except Exception:
            logger.exception("STT engine release failed")
    _release_mlx_cache()
    logger.info("STT model unloaded (idle)")


def _request_timeout(config: Config) -> float:
    """Inference (and on-demand load) timeout in seconds. A seam for tests."""
    return float(config.stt_server.request_timeout_seconds)


def _model_ready() -> bool:
    return state.ready and state.engine is not None and state.processor is not None


def _load_model_job(config: Config) -> None:
    """Worker-thread job: load + warmup. Records the error for /healthz."""
    try:
        _load_model_sync(config)
    except Exception as e:
        state.ready = False
        state.engine = None
        state.processor = None
        state.warmup_error = str(e)
        logger.exception("STT model load failed: %s", e)
        raise
    finally:
        state.loading = False


async def _ensure_model_loaded(lease: Lease, config: Config, timeout: Optional[float]) -> None:
    """Load the model on the worker thread if needed. Caller holds ``lease``."""
    if _model_ready():
        return
    state.loading = True
    state.warmup_error = None
    logger.info("STT loading model on demand…")
    try:
        await lease.run(_load_model_job, config, timeout=timeout, kind="load")
    except JobTimeoutError as e:
        # The load goes on in the background and keeps the slot; retrying is right.
        raise APIError(
            503,
            err.MODEL_LOADING,
            "STT model is still loading; retry shortly",
            retry_after=err.RETRY_AFTER_LOADING_SECONDS,
        ) from e
    except Exception as e:
        raise APIError(500, err.MODEL_LOAD_FAILED, f"STT model load failed: {e}") from e


def _transcribe_job(
    audio: np.ndarray,
    *,
    sample_rate: int,
    want_words: bool,
    language: Optional[str],
    requested_language: str,
    initial_prompt: Optional[str],
    task: str = "transcribe",
) -> tuple[dict, float]:
    """Worker-thread job: prepare audio and run the engine. Returns (payload, seconds)."""
    engine, processor = state.engine, state.processor
    if engine is None or processor is None:
        raise RuntimeError("STT model is not loaded")
    state.last_used_at = time.time()
    try:
        prepared = processor.prepare_for_whisper(audio)
        duration_s = len(prepared) / float(sample_rate)
        if duration_s >= 60:
            logger.info("STT long job: %.1fs audio (concurrency=1)", duration_s)
        payload = engine.transcribe_detailed(
            prepared,
            word_timestamps=want_words,
            language=language,
            requested_language=requested_language,
            initial_prompt=initial_prompt,
            # Only Whisper knows `task`; transcription keeps the old call for other engines.
            **({"task": task} if task != "transcribe" else {}),
        )
        return payload or {}, duration_s
    finally:
        state.last_used_at = time.time()


async def _switch_model(new_config: Config) -> None:
    """Unload the current model and load the one ``new_config`` selects.

    Runs on the inference worker like every other model job, so it waits for a
    running transcription instead of pulling the model out from under it. On a
    load failure the previous selection is restored (and loads on the next
    request); nothing is persisted by this function.
    """
    worker = state.worker
    if worker is None or state.config is None:
        raise APIError(503, err.MODEL_LOADING, "STT is not initialized yet")
    try:
        lease = await worker.acquire(
            PRIORITY_INTERACTIVE, timeout=float(state.config.stt_server.queue_timeout_seconds)
        )
    except QueueTimeoutError as e:
        raise APIError(
            429, err.BUSY, "STT busy: try switching again shortly",
            retry_after=err.RETRY_AFTER_BUSY_SECONDS,
        ) from e
    previous = state.config
    try:
        if state.engine is not None or state.ready:
            await lease.run(_unload_model_sync, kind="unload")
        state.config = new_config
        state.model_name = _configured_model_name(new_config)
        state.loading = True
        state.warmup_error = None
        logger.info("STT switching model → %s", state.model_name)
        try:
            await lease.run(
                _load_model_job, new_config, timeout=_request_timeout(new_config), kind="load"
            )
        except JobTimeoutError as e:
            raise APIError(
                503, err.MODEL_LOADING, "New model is still loading; retry shortly",
                retry_after=err.RETRY_AFTER_LOADING_SECONDS,
            ) from e
        except Exception as e:
            state.config = previous
            state.model_name = _configured_model_name(previous)
            raise APIError(500, err.MODEL_LOAD_FAILED, f"Could not load the new model: {e}") from e
    finally:
        lease.close()


async def _idle_unload_once() -> bool:
    """One idle-unload check. True if the model was unloaded."""
    cfg, worker = state.config, state.worker
    if cfg is None or worker is None:
        return False
    idle_after = cfg.stt_server.idle_unload_seconds
    if idle_after <= 0 or not state.ready or state.engine is None or state.loading:
        return False
    # A job whose request already got a 504 still counts: MLX is still using the model.
    if worker.active_jobs > 0 or worker.busy:
        return False
    if time.time() - state.last_used_at < idle_after:
        return False
    lease = worker.try_acquire()
    if lease is None:
        return False
    try:
        if not state.ready or time.time() - state.last_used_at < idle_after:
            return False
        logger.info(
            "STT idle %.0fs >= %ss — unloading model",
            time.time() - state.last_used_at,
            idle_after,
        )
        await lease.run(_unload_model_sync, kind="unload")
        return True
    finally:
        lease.close()


async def _idle_unload_loop() -> None:
    """Background: unload weights after idle_unload_seconds without traffic."""
    while True:
        try:
            await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
            await _idle_unload_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("STT idle unload loop error")


def create_app(config: Config) -> FastAPI:
    """Build FastAPI app bound to config (used by tests and CLI)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state.config = config
        state.ready = False
        state.loading = False
        state.warmup_error = None
        state.engine = None
        state.processor = None
        state.last_used_at = 0.0
        worker = InferenceWorker()
        state.worker = worker
        server_cfg = config.stt_server
        logger.info(
            "STT server starting: bind=%s:%s engine=%s preload=%s idle_unload=%ss "
            "queue_timeout=%ss max_audio=%ss",
            server_cfg.host,
            server_cfg.port,
            server_cfg.engine,
            server_cfg.preload_on_start,
            server_cfg.idle_unload_seconds,
            server_cfg.queue_timeout_seconds,
            server_cfg.max_audio_seconds,
        )
        state.model_name = _configured_model_name(config)

        if server_cfg.preload_on_start:
            lease = await worker.acquire(PRIORITY_INTERACTIVE, timeout=None)
            state.loading = True
            try:
                await lease.run(_load_model_job, config, kind="load")
                logger.info("STT ready (preloaded): model=%s", state.model_name)
            except Exception:
                pass  # logged by the job; /healthz last_error and /readyz report it
            finally:
                lease.close()
        else:
            logger.info(
                "STT process up; model not loaded (on-demand). readyz=503 until first request"
            )

        state.idle_task = asyncio.create_task(_idle_unload_loop())
        try:
            yield
        finally:
            if state.idle_task is not None:
                state.idle_task.cancel()
                try:
                    await state.idle_task
                except asyncio.CancelledError:
                    pass
                state.idle_task = None
            busy = worker.active_jobs > 0
            worker.shutdown()
            state.ready = False
            state.engine = None
            state.processor = None
            if busy:
                logger.warning("STT shutdown while a job is running; MLX cache left as is")
            else:
                _release_mlx_cache()

    app = FastAPI(title="VTTv2 Local STT", version=config.app.version, lifespan=lifespan)
    install_error_handlers(app)
    register_model_routes(
        app, ModelHost(get_config=lambda: state.config or config, switch=_switch_model)
    )
    max_upload_mb = config.stt_server.max_upload_mb
    app.add_middleware(
        BodySizeLimitMiddleware,
        max_bytes=max_upload_mb * 1024 * 1024 + MULTIPART_OVERHEAD_BYTES,
        message=f"File too large (max {max_upload_mb} MB)",
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        worker = state.worker
        return {
            "status": "ok",
            "service": "vtt2-stt",
            "ready": state.ready,
            "loading": state.loading,
            "last_error": state.warmup_error,
            "active_jobs": worker.active_jobs if worker else 0,
            "queued": worker.queued if worker else 0,
            "model": state.model_name or None,
            "preload_on_start": bool(
                state.config.stt_server.preload_on_start if state.config else True
            ),
            "idle_unload_seconds": (
                state.config.stt_server.idle_unload_seconds if state.config else 0
            ),
        }

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        if state.ready and state.engine is not None:
            return JSONResponse(
                status_code=200,
                content={"status": "ready", "model": state.model_name},
            )
        if state.loading:
            detail = "model loading"
        elif state.warmup_error:
            detail = state.warmup_error
        elif state.config and not state.config.stt_server.preload_on_start:
            detail = "model unloaded (idle or not yet loaded); POST will load on demand"
        else:
            detail = "model not loaded"
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": detail, "loading": state.loading},
        )

    async def _handle_audio(
        file: UploadFile,
        model: Optional[str],
        language: Optional[str],
        response_format: str,
        prompt: Optional[str],
        timestamp_granularities: Optional[str],
        timestamp_granularities_bracket: Optional[str],
        task: str = "transcribe",
    ):
        """Shared body of /v1/audio/transcriptions and /v1/audio/translations."""
        cfg, worker = state.config, state.worker
        if cfg is None or worker is None:
            raise APIError(
                503,
                err.MODEL_LOADING,
                "STT not initialized",
                retry_after=err.RETRY_AFTER_LOADING_SECONDS,
            )

        fmt = (response_format or "json").strip().lower()
        if fmt not in ("json", "verbose_json", "text"):
            raise APIError(
                400,
                err.INVALID_REQUEST,
                "response_format must be json, verbose_json, or text",
            )
        want_words = _want_word_timestamps(
            timestamp_granularities, timestamp_granularities_bracket
        )

        config_lang = _profile_language(cfg)
        try:
            requested_label, effective_language = resolve_request_language(
                language, config_lang
            )
        except RejectedLanguage as e:
            raise APIError(400, err.UNSUPPORTED_LANGUAGE, str(e)) from e

        initial_prompt: Optional[str] = None
        if prompt is not None and prompt.strip():
            initial_prompt = prompt.strip()
            if len(initial_prompt) > PROMPT_MAX_CHARS:
                raise APIError(
                    400,
                    err.INVALID_REQUEST,
                    f"prompt longer than {PROMPT_MAX_CHARS} characters",
                )

        # The body limit middleware already capped the request; this is the exact file limit.
        max_bytes = cfg.stt_server.max_upload_mb * 1024 * 1024
        data = await file.read()
        if len(data) > max_bytes:
            raise APIError(
                413,
                err.FILE_TOO_LARGE,
                f"File too large (max {cfg.stt_server.max_upload_mb} MB)",
            )
        if not data:
            raise APIError(400, err.INVALID_AUDIO, "Empty file")

        if model:
            logger.info("STT request model=%s (server uses %s)", model, state.model_name)
        if fmt != "json" or want_words:
            logger.info(
                "STT request response_format=%s timestamp_granularities=%s",
                fmt,
                timestamp_granularities,
            )

        try:
            # Off the event loop: ffmpeg can take seconds, and /healthz must stay live.
            audio = await asyncio.to_thread(
                decode_audio_bytes,
                data,
                filename=file.filename,
                content_type=file.content_type,
                sample_rate=cfg.audio.sample_rate,
            )
        except AudioDecodeError as e:
            raise APIError(400, err.INVALID_AUDIO, str(e)) from e
        except Exception as e:
            logger.warning("STT: unexpected audio decode error: %s", e)
            raise APIError(
                400, err.INVALID_AUDIO, f"Не удалось декодировать аудио: {e}"
            ) from e
        del data

        audio_seconds = audio.shape[0] / float(cfg.audio.sample_rate)
        max_seconds = cfg.stt_server.max_audio_seconds
        if audio_seconds > max_seconds:
            raise APIError(
                413,
                err.AUDIO_TOO_LONG,
                f"Audio is {audio_seconds:.0f}s long; the limit is {max_seconds}s "
                "(stt_server.max_audio_seconds)",
            )

        try:
            lease = await worker.acquire(
                priority_for(audio_seconds),
                timeout=float(cfg.stt_server.queue_timeout_seconds),
            )
        except QueueTimeoutError as e:
            if state.loading:
                raise APIError(
                    503,
                    err.MODEL_LOADING,
                    "STT model is loading; retry shortly",
                    retry_after=err.RETRY_AFTER_LOADING_SECONDS,
                ) from e
            raise APIError(
                429,
                err.BUSY,
                "STT busy: another transcription is running",
                retry_after=err.RETRY_AFTER_BUSY_SECONDS,
            ) from e

        # The model may have been switched (/v1/models/{id}/activate) while this
        # request waited for the slot; use the config that is active now.
        cfg = state.config or cfg
        timeout = _request_timeout(cfg)
        start = time.time()
        try:
            await _ensure_model_loaded(lease, cfg, timeout)
            try:
                payload, duration_s = await lease.run(
                    _transcribe_job,
                    audio,
                    sample_rate=cfg.audio.sample_rate,
                    want_words=want_words,
                    language=effective_language,
                    requested_language=requested_label,
                    initial_prompt=initial_prompt,
                    task=task,
                    timeout=timeout,
                    kind=task,
                    audio_seconds=audio_seconds,
                )
            except JobTimeoutError as e:
                logger.error(
                    "STT transcription timeout after %.0fs (%.1fs audio); "
                    "the job keeps the model until it returns",
                    timeout,
                    audio_seconds,
                )
                raise APIError(
                    504,
                    err.TRANSCRIPTION_TIMEOUT,
                    f"Transcription did not finish in {timeout:.0f}s "
                    "(stt_server.request_timeout_seconds)",
                ) from e
            except Exception as e:
                logger.exception("STT transcription failed: %s", e)
                raise APIError(500, err.TRANSCRIPTION_FAILED, "Transcription failed") from e
        finally:
            lease.close()

        payload = _strip_artifacts_payload(payload, cfg)
        payload["duration"] = float(payload.get("duration") or duration_s)
        elapsed = time.time() - start
        logger.info(
            "STT ok: %.1fs audio → %d chars / %d segments in %.2fs format=%s",
            duration_s,
            len(payload.get("text") or ""),
            len(payload.get("segments") or []),
            elapsed,
            fmt,
        )
        text = payload.get("text") or ""
        reported_language = payload.get("language") or effective_language
        if fmt == "text":
            return PlainTextResponse(content=text)
        if fmt == "verbose_json":
            return {
                "task": task,
                "language": reported_language,
                "duration": payload["duration"],
                "text": text,
                "segments": payload.get("segments") or [],
            }
        body: dict[str, Any] = {"text": text}
        if requested_label not in ("omitted", "blank") and reported_language:
            body["language"] = reported_language
        return body

    @app.post("/v1/audio/transcriptions")
    async def transcriptions(
        file: UploadFile = File(...),
        model: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        response_format: str = Form("json"),
        prompt: Optional[str] = Form(None),
        timestamp_granularities: Optional[str] = Form(None),
        timestamp_granularities_bracket: Optional[str] = Form(
            None, alias="timestamp_granularities[]"
        ),
    ):
        return await _handle_audio(
            file, model, language, response_format, prompt,
            timestamp_granularities, timestamp_granularities_bracket,
        )

    @app.post("/v1/audio/translations")
    async def translations(
        file: UploadFile = File(...),
        model: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        response_format: str = Form("json"),
        prompt: Optional[str] = Form(None),
    ):
        """Speech in any language → English text (Whisper's built-in translate task).

        OpenAI-compatible. ``language`` is the optional *source* language hint.
        """
        if state.config is not None:
            reason = _translation_unsupported(state.config)
            if reason:
                raise APIError(400, err.TRANSLATION_UNSUPPORTED, reason)
        return await _handle_audio(
            file, model, language, response_format, prompt, None, None, task="translate",
        )

    return app


def _translation_unsupported(config: Config) -> Optional[str]:
    """Why the loaded model can't translate, or None if it can.

    Only Whisper translates (to English). large-v3-turbo was trained for
    transcription only and translates poorly, so catalog entries say so.
    """
    from model_catalog.registry import active_selection, load_catalog

    family, repo = active_selection(config)
    if family not in WHISPER_FAMILY_ENGINES:
        return (
            "Translation to English needs a Whisper model; the active model only transcribes. "
            "Pick Whisper large-v3 in the model menu."
        )
    spec = load_catalog().find(family, repo)
    if spec is not None and not spec.translates:
        return f"{spec.title} translates poorly; pick Whisper large-v3 (or its 8-bit) for translation."
    return None


def run_server(config: Config) -> None:
    """Block and serve (used by CLI --serve-stt)."""
    host = config.stt_server.host
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(
            f"Refusing to bind non-loopback host: {host}. "
            "Set stt_server.host to 127.0.0.1"
        )
    if config.stt_server.engine == "qwen3_asr":
        from transcription.qwen_engine import ensure_qwen_installed

        try:
            ensure_qwen_installed()
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
    port = config.stt_server.port
    app = create_app(config)
    logger.info("Listening on http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main_from_config_path(config_path: str = "config.yaml") -> int:
    """Load config from project root and run server."""
    from utils.logger import setup_logging

    project_root = Path.cwd()
    if not (project_root / config_path).exists():
        project_root = Path(__file__).resolve().parent.parent.parent
    config_file = project_root / config_path
    config = Config.from_yaml(str(config_file), project_root)
    setup_logging(
        level=config.logging.level,
        format_string=config.logging.format,
        log_file=config.logging.file,
    )
    run_server(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_from_config_path())
