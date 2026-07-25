"""
Local OpenAI-compatible STT HTTP API.

Owns mlx_whisper (or whisper_cpp) in one process. Menubar and agents are clients.
Bind: loopback only. Concurrency: 1.
"""
from __future__ import annotations

import asyncio
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
        self.warmup_error: Optional[str] = None
        self.config: Optional[Config] = None
        self.engine: Optional[TranscriptionEngineWrapper] = None
        self.processor: Optional[AudioProcessor] = None
        self.lock = asyncio.Lock()
        self.model_name: str = ""


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
        logger.info("STT: удалён хвостовой артефакт Whisper (−%d символов)", len(text) - len(cleaned))
    return cleaned


def _warmup(engine: TranscriptionEngineWrapper, sample_rate: int) -> None:
    """Force model load with short silence (not meant to produce text)."""
    silence = np.zeros(int(sample_rate * 0.5), dtype=np.float32)
    try:
        engine.transcribe(silence)
    except Exception as e:
        # Empty / no-speech can still load weights; only fail on hard errors
        msg = str(e).lower()
        if "не установлен" in msg or "not found" in msg or "не найден" in msg:
            raise
        logger.warning("STT warmup returned error (model likely loaded): %s", e)


def create_app(config: Config) -> FastAPI:
    """Build FastAPI app bound to config (used by tests and CLI)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state.config = config
        state.ready = False
        state.warmup_error = None
        server_cfg = config.stt_server
        logger.info(
            "STT server starting: bind=%s:%s engine=%s",
            server_cfg.host,
            server_cfg.port,
            server_cfg.engine,
        )
        try:
            eng_config = _server_engine_config(config)
            state.engine = TranscriptionEngineWrapper(eng_config)
            state.processor = AudioProcessor()
            if eng_config.transcription.mlx_whisper:
                state.model_name = eng_config.transcription.mlx_whisper.model_name
            else:
                state.model_name = server_cfg.engine
            await asyncio.to_thread(
                _warmup, state.engine, eng_config.audio.sample_rate
            )
            state.ready = True
            logger.info("STT ready: model=%s", state.model_name)
        except Exception as e:
            state.warmup_error = str(e)
            state.ready = False
            logger.exception("STT warmup failed: %s", e)
        yield
        state.ready = False
        state.engine = None
        state.processor = None

    app = FastAPI(title="VTTv2 Local STT", version=config.app.version, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "vtt2-stt",
            "ready": state.ready,
            "model": state.model_name or None,
        }

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        if state.ready and state.engine is not None:
            return JSONResponse(
                status_code=200,
                content={"status": "ready", "model": state.model_name},
            )
        detail = state.warmup_error or "model not loaded"
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": detail},
        )

    @app.post("/v1/audio/transcriptions")
    async def transcriptions(
        request: Request,
        file: UploadFile = File(...),
        model: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
    ) -> dict[str, Any]:
        if not state.ready or state.engine is None or state.config is None:
            raise HTTPException(
                status_code=503,
                detail=state.warmup_error or "STT not ready",
            )

        cfg = state.config
        max_bytes = cfg.stt_server.max_upload_mb * 1024 * 1024
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > max_bytes + 1024 * 64:  # multipart overhead slack
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

        assert state.processor is not None
        audio = state.processor.prepare_for_whisper(audio)

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
