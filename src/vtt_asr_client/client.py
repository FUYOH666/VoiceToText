"""
OpenAI-compatible audio transcription client (/v1/audio/transcriptions).
Used by Mac remote_asr and Linux F9.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2


@dataclass
class ASRClientConfig:
    base_url: str
    timeout: int = 60
    model: str = "cstr/whisper-large-v3-turbo-int8_float32"
    language: Optional[str] = "auto"
    transcription_endpoint: str = "/v1/audio/transcriptions"
    response_format: str = "json"

    @property
    def transcription_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.transcription_endpoint}"


class ASRClient:
    """HTTP client for private ASR service."""

    def __init__(self, config: ASRClientConfig):
        self.config = config

    def healthz(self, timeout: float = 5) -> bool:
        url = f"{self.config.base_url.rstrip('/')}/healthz"
        try:
            resp = requests.get(url, timeout=timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def transcribe_file(self, audio_file: Path) -> str:
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        with open(audio_file, "rb") as f:
            wav_bytes = f.read()
        return self.transcribe_bytes(wav_bytes, filename=audio_file.name)

    def transcribe_bytes(
        self,
        wav_bytes: bytes,
        filename: str = "audio.wav",
    ) -> str:
        return transcribe_wav_bytes(
            wav_bytes,
            config=self.config,
            filename=filename,
        )


def transcribe_wav_bytes(
    wav_bytes: bytes,
    *,
    config: ASRClientConfig,
    filename: str = "audio.wav",
) -> str:
    """POST multipart transcription with retries on connection/timeout errors."""
    files = {"file": (filename, wav_bytes, "audio/wav")}
    data: dict[str, str] = {"model": config.model}
    if config.language and str(config.language).lower() != "auto":
        data["language"] = str(config.language)
    if config.response_format:
        data["response_format"] = config.response_format

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                config.transcription_url,
                files=files,
                data=data,
                timeout=config.timeout,
            )
            response.raise_for_status()
            if config.response_format == "json":
                result = response.json()
                return str(result.get("text", "")).strip()
            return response.text.strip()
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                logger.warning(
                    "ASR attempt %s/%s failed, retry in %ss: %s",
                    attempt,
                    MAX_RETRIES,
                    RETRY_DELAY_SEC,
                    e,
                )
                time.sleep(RETRY_DELAY_SEC)
            else:
                raise
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            body = e.response.text[:200] if e.response is not None else ""
            logger.error("ASR HTTP error %s: %s", status, body)
            raise RuntimeError(f"ASR service error: {status}") from e

    if last_error:
        raise last_error
    return ""
