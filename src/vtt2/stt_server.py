"""
Local OpenAI-compatible STT HTTP API.

Owns mlx_whisper (or whisper_cpp) in one process. Menubar and agents are clients.
Bind: loopback only. Concurrency: 1.

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
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from audio.decode import AudioDecodeError, decode_audio_bytes
from audio.processor import AudioProcessor
from config.loader import Config
from transcription.engine import TranscriptionEngineWrapper

logger = logging.getLogger(__name__)


class STTState:
    """Mutable server state (model readiness + engine)."""

    def __init__(self) -> None:
        self.ready: bool = False
        self.loading: bool = False
        self.warmup_error: Optional[str] = None
        self.config: Optional[Config] = None
        self.engine: Optional[TranscriptionEngineWrapper] = None
        self.processor: Optional[AudioProcessor] = None
        self.lock = asyncio.Lock()
        self.model_name: str = ""
        self.last_used_at: float = 0.0
        self.idle_task: Optional[asyncio.Task] = None


state = STTState()


def _server_engine_config(config: Config) -> Config:
    """Clone-like override: transcription.engine = stt_server.engine for in-process load."""
    data = config.model_dump()
    data["transcription"]["engine"] = config.stt_server.engine
    return Config(**data)


def _strip_artifacts(text: str, config: Config) -> str:
    if not config.text_processing.strip_whisper_tail_artifacts:
        return text
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


def _load_model_sync(config: Config) -> None:
    """Load engine + warmup (blocking; call via to_thread)."""
    eng_config = _server_engine_config(config)
    engine = TranscriptionEngineWrapper(eng_config)
    processor = AudioProcessor()
    if eng_config.transcription.mlx_whisper:
        state.model_name = eng_config.transcription.mlx_whisper.model_name
    else:
        state.model_name = config.stt_server.engine
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
    state.engine = None
    state.processor = None
    _release_mlx_cache()
    logger.info("STT model unloaded (idle)")


async def _ensure_model_loaded(config: Config) -> None:
    """Load model if needed. Caller must hold state.lock."""
    if state.ready and state.engine is not None and state.processor is not None:
        return
    state.loading = True
    state.warmup_error = None
    try:
        logger.info("STT loading model on demand…")
        await asyncio.to_thread(_load_model_sync, config)
    except Exception as e:
        state.ready = False
        state.engine = None
        state.processor = None
        state.warmup_error = str(e)
        logger.exception("STT model load failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail=f"STT model load failed: {e}",
        ) from e
    finally:
        state.loading = False


async def _idle_unload_loop() -> None:
    """Background: unload weights after idle_unload_seconds without traffic."""
    while True:
        try:
            await asyncio.sleep(15)
            cfg = state.config
            if cfg is None:
                continue
            idle_after = cfg.stt_server.idle_unload_seconds
            if idle_after <= 0:
                continue
            if not state.ready or state.engine is None:
                continue
            if state.loading:
                continue
            if state.lock.locked():
                continue
            idle_for = time.time() - state.last_used_at
            if idle_for < idle_after:
                continue
            async with state.lock:
                if not state.ready or state.engine is None:
                    continue
                if time.time() - state.last_used_at < idle_after:
                    continue
                logger.info(
                    "STT idle %.0fs >= %ss — unloading model",
                    time.time() - state.last_used_at,
                    idle_after,
                )
                await asyncio.to_thread(_unload_model_sync)
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
        server_cfg = config.stt_server
        logger.info(
            "STT server starting: bind=%s:%s engine=%s preload=%s idle_unload=%ss",
            server_cfg.host,
            server_cfg.port,
            server_cfg.engine,
            server_cfg.preload_on_start,
            server_cfg.idle_unload_seconds,
        )
        if eng_name := (
            config.transcription.mlx_whisper.model_name
            if config.transcription.mlx_whisper
            else server_cfg.engine
        ):
            state.model_name = eng_name

        if server_cfg.preload_on_start:
            try:
                await asyncio.to_thread(_load_model_sync, config)
                logger.info("STT ready (preloaded): model=%s", state.model_name)
            except Exception as e:
                state.warmup_error = str(e)
                state.ready = False
                logger.exception("STT preload failed: %s", e)
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
            state.ready = False
            state.engine = None
            state.processor = None
            _release_mlx_cache()

    app = FastAPI(title="VTTv2 Local STT", version=config.app.version, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "vtt2-stt",
            "ready": state.ready,
            "loading": state.loading,
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

    @app.post("/v1/audio/transcriptions")
    async def transcriptions(
        request: Request,
        file: UploadFile = File(...),
        model: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
    ) -> dict[str, Any]:
        if state.config is None:
            raise HTTPException(status_code=503, detail="STT not initialized")

        cfg = state.config
        max_bytes = cfg.stt_server.max_upload_mb * 1024 * 1024
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > max_bytes + 1024 * 64:
                    raise HTTPException(status_code=413, detail="File too large")
            except ValueError:
                pass

        data = await file.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (max {cfg.stt_server.max_upload_mb} MB)",
            )
        if not data:
            raise HTTPException(status_code=400, detail="Empty file")

        if model:
            logger.info("STT request model=%s (server uses %s)", model, state.model_name)
        if language:
            logger.info("STT request language=%s", language)

        try:
            audio = decode_audio_bytes(
                data,
                filename=file.filename,
                content_type=file.content_type,
                sample_rate=cfg.audio.sample_rate,
            )
        except AudioDecodeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        acquired = False
        try:
            try:
                await asyncio.wait_for(
                    state.lock.acquire(),
                    timeout=float(cfg.stt_server.request_timeout_seconds),
                )
                acquired = True
            except asyncio.TimeoutError as e:
                raise HTTPException(
                    status_code=503, detail="STT busy (queue timeout)"
                ) from e

            await _ensure_model_loaded(cfg)
            assert state.engine is not None and state.processor is not None
            audio = state.processor.prepare_for_whisper(audio)
            state.last_used_at = time.time()

            start = time.time()
            try:
                text = await asyncio.wait_for(
                    asyncio.to_thread(state.engine.transcribe, audio),
                    timeout=float(cfg.stt_server.request_timeout_seconds),
                )
            except asyncio.TimeoutError as e:
                raise HTTPException(
                    status_code=503, detail="Transcription timeout"
                ) from e
            except Exception as e:
                logger.exception("STT transcription failed: %s", e)
                raise HTTPException(status_code=500, detail="Transcription failed") from e

            state.last_used_at = time.time()
            text = _strip_artifacts(text or "", cfg)
            elapsed = time.time() - start
            duration_s = len(audio) / float(cfg.audio.sample_rate)
            logger.info(
                "STT ok: %.1fs audio → %d chars in %.2fs lang=%s",
                duration_s,
                len(text),
                elapsed,
                language or "auto",
            )
            body: dict[str, Any] = {"text": text}
            if language:
                body["language"] = language
            return body
        finally:
            if acquired:
                state.lock.release()

    return app


def run_server(config: Config) -> None:
    """Block and serve (used by CLI --serve-stt)."""
    host = config.stt_server.host
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(
            f"Refusing to bind non-loopback host: {host}. "
            "Set stt_server.host to 127.0.0.1"
        )
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
