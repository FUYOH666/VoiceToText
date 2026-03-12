"""
Удалённый ASR через LocalAI-совместимый API (Tailscale).
Транскрипция на Linux GPU сервере — разгружает MacBook.
"""
import io
import logging
import os
import time
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class RemoteASRTranscriber:
    """Транскрипция через удалённый ASR (LocalAI / whisper.cpp server)"""

    def __init__(self, config):
        self.config = config
        self.asr_config = config.transcription.remote_asr
        self.sample_rate = config.audio.sample_rate

        if not HTTPX_AVAILABLE:
            raise RuntimeError("httpx не установлен. Установите: pip install httpx")

        base_url = self._base_url()
        logger.info("RemoteASRTranscriber инициализирован")
        logger.info(f"ASR URL: {base_url}{self.asr_config.path}")
        logger.info(f"Модель: {self.asr_config.model}")

    def _base_url(self) -> str:
        base = os.getenv("LOCAL_AI_ASR_BASE_URL", "").rstrip("/")
        if base:
            return base
        host = self.asr_config.host
        port = self.asr_config.port
        return f"http://{host}:{port}"

    def _check_health(self) -> bool:
        """Проверка доступности ASR через GET /healthz"""
        try:
            base = self._base_url()
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{base}/healthz")
                if r.status_code == 200:
                    data = r.json()
                    model = data.get("model_info", {}).get("model_path", "?")
                    gpu = data.get("gpu_info", {}).get("device_name", "?")
                    logger.info(f"ASR доступен: {model}, GPU: {gpu}")
                    return True
                return False
        except Exception as e:
            logger.warning(f"ASR health check: {e}")
            return False

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрипция аудио через удалённый ASR.

        Args:
            audio_data: numpy float32, моно, 16kHz

        Returns:
            Транскрибированный текст
        """
        start = time.time()

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Нормализация
        max_val = max(abs(audio_data.max()), abs(audio_data.min()))
        if max_val > 1.0:
            audio_data = audio_data / max_val

        # Конвертация в WAV bytes
        buf = io.BytesIO()
        sf.write(buf, audio_data, self.sample_rate, format="WAV")
        buf.seek(0)

        base = self._base_url()
        url = f"{base}{self.asr_config.path}"

        try:
            with httpx.Client(timeout=self.asr_config.timeout_seconds) as client:
                files = {"file": ("audio.wav", buf, "audio/wav")}
                data = {"model": self.asr_config.model}

                response = client.post(url, files=files, data=data)
                response.raise_for_status()

                result = response.json()
                text = result.get("text") or result.get("transcription") or ""

                elapsed = time.time() - start
                duration_s = len(audio_data) / self.sample_rate
                logger.info(
                    f"Remote ASR: {len(text)} символов за {elapsed:.2f}с "
                    f"({duration_s:.1f}s аудио)"
                )
                return text.strip()

        except httpx.ConnectError as e:
            logger.error(f"ASR недоступен (проверьте Tailscale): {e}")
            raise RuntimeError(f"Не удалось подключиться к ASR: {e}") from e
        except httpx.TimeoutException:
            logger.error("ASR: таймаут запроса")
            raise RuntimeError("Таймаут запроса к ASR") from None
        except httpx.HTTPStatusError as e:
            logger.error(f"ASR HTTP {e.response.status_code}: {e.response.text}")
            raise RuntimeError(f"Ошибка ASR: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Ошибка Remote ASR: {e}")
            raise RuntimeError(f"Ошибка транскрипции: {e}") from e
