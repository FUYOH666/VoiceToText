"""
Thin HTTP client to local STT (ai.vtt2.stt).
Menubar does not load MLX — one model resident in the STT process.
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

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрипция через POST /v1/audio/transcriptions.

        Args:
            audio_data: numpy float32, моно, 16kHz

        Returns:
            Текст (артефакты уже сняты на сервере)
        """
        start = time.time()

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        max_val = max(abs(float(audio_data.max())), abs(float(audio_data.min())), 1e-9)
        if max_val > 1.0:
            audio_data = audio_data / max_val

        buf = io.BytesIO()
        sf.write(buf, audio_data, self.sample_rate, format="WAV")
        buf.seek(0)

        url = f"{self._base_url()}{self.stt_config.path}"
        timeout = self.stt_config.timeout_seconds

        try:
            with httpx.Client(timeout=timeout) as client:
                # Fail fast if STT not ready (no silent in-process MLX fallback)
                ready = client.get(f"{self._base_url()}/readyz")
                if ready.status_code != 200:
                    detail = ready.text[:200]
                    raise RuntimeError(
                        f"Локальный STT не готов (readyz={ready.status_code}): {detail}. "
                        "Запустите: uv run python src/vtt2/main.py --serve-stt "
                        "или --install (ai.vtt2.stt)"
                    )

                files = {"file": ("audio.wav", buf, "audio/wav")}
                response = client.post(url, files=files)
                response.raise_for_status()
                result = response.json()
                text = result.get("text") or result.get("transcription") or ""

                elapsed = time.time() - start
                duration_s = len(audio_data) / self.sample_rate
                logger.info(
                    "Local STT: %d символов за %.2fс (%.1fs аудио)",
                    len(text),
                    elapsed,
                    duration_s,
                )
                return text.strip()

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
            logger.error("Local STT HTTP %s: %s", e.response.status_code, e.response.text)
            raise RuntimeError(
                f"Ошибка локального STT: {e.response.status_code}"
            ) from e
