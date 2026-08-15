"""
Thin HTTP client to local STT (ai.vtt2.stt).
Menubar does not load MLX — one model resident (or on-demand) in the STT process.
"""
from __future__ import annotations

import io
import logging
import time

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class LocalSTTTranscriber:
    """Транскрипция через локальный OpenAI-compatible STT на loopback."""

    def __init__(self, config):
        self.config = config
        self.stt_config = config.transcription.local_stt
        if self.stt_config is None:
            raise RuntimeError("local_stt требует transcription.local_stt в конфиге")
        self.sample_rate = config.audio.sample_rate

        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx не установлен. Установите: uv add httpx")

        base = self.stt_config.base_url.rstrip("/")
        logger.info("LocalSTTTranscriber инициализирован")
        logger.info("STT URL: %s%s", base, self.stt_config.path)

    def _base_url(self) -> str:
        return self.stt_config.base_url.rstrip("/")

    def check_ready(self) -> bool:
        """GET /readyz — модель прогрета."""
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self._base_url()}/readyz")
                return r.status_code == 200
        except Exception as e:
            logger.warning("Local STT readyz: %s", e)
            return False

    def _assert_process_up(self, client: httpx.Client) -> None:
        """healthz must be 200; readyz may be 503 when idle-unloaded."""
        try:
            health = client.get(f"{self._base_url()}/healthz")
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Не удалось подключиться к локальному STT ({self._base_url()}): {e}. "
                "Убедитесь, что ai.vtt2.stt запущен."
            ) from e
        if health.status_code != 200:
            raise RuntimeError(
                f"Локальный STT healthz={health.status_code}: {health.text[:200]}"
            )

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрипция через POST /v1/audio/transcriptions.

        On-demand: if model was idle-unloaded, server loads on POST (may take a while).
        Retries transient 503 while loading within warmup_wait_seconds.
        """
        start = time.time()

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        max_val = max(abs(float(audio_data.max())), abs(float(audio_data.min())), 1e-9)
        if max_val > 1.0:
            audio_data = audio_data / max_val

        buf = io.BytesIO()
        sf.write(buf, audio_data, self.sample_rate, format="WAV")
        wav_bytes = buf.getvalue()

        url = f"{self._base_url()}{self.stt_config.path}"
        timeout = self.stt_config.timeout_seconds
        warmup_wait = getattr(self.stt_config, "warmup_wait_seconds", 180) or 0
        deadline = start + warmup_wait + timeout

        try:
            with httpx.Client(timeout=timeout) as client:
                self._assert_process_up(client)

                ready = client.get(f"{self._base_url()}/readyz")
                if ready.status_code != 200:
                    logger.info(
                        "Local STT not ready yet (%s) — POST will load on demand",
                        ready.text[:120],
                    )

                attempt = 0
                while True:
                    attempt += 1
                    files = {
                        "file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")
                    }
                    response = client.post(url, files=files)
                    if response.status_code == 200:
                        result = response.json()
                        text = result.get("text") or result.get("transcription") or ""
                        elapsed = time.time() - start
                        duration_s = len(audio_data) / self.sample_rate
                        logger.info(
                            "Local STT: %d символов за %.2fс (%.1fs аудио, attempt=%d)",
                            len(text),
                            elapsed,
                            duration_s,
                            attempt,
                        )
                        return text.strip()

                    if response.status_code == 503 and time.time() < deadline:
                        detail = response.text[:200]
                        logger.info(
                            "Local STT 503 (warmup/busy), retry in 2s: %s", detail
                        )
                        time.sleep(2)
                        continue

                    response.raise_for_status()

        except httpx.ConnectError as e:
            logger.error("Local STT недоступен: %s", e)
            raise RuntimeError(
                f"Не удалось подключиться к локальному STT ({self._base_url()}): {e}. "
                "Убедитесь, что ai.vtt2.stt запущен."
            ) from e
        except httpx.TimeoutException:
            logger.error("Local STT: таймаут запроса")
            raise RuntimeError("Таймаут запроса к локальному STT") from None
        except httpx.HTTPStatusError as e:
            logger.error(
                "Local STT HTTP %s: %s", e.response.status_code, e.response.text
            )
            raise RuntimeError(
                f"Ошибка локального STT: {e.response.status_code}"
            ) from e
