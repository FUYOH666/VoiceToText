"""
Транскрипция через удаленный ASR сервис (Linux GPU сервер через TailScale)
"""
from __future__ import annotations

import io
import logging
import time

import numpy as np
import requests
import soundfile as sf

from vtt_asr_client.client import ASRClient, ASRClientConfig, transcribe_wav_bytes

logger = logging.getLogger(__name__)


class RemoteASRTranscriber:
    """Транскрипция через удаленный ASR сервис (OpenAI-compatible API)"""

    def __init__(self, config):
        self.config = config
        self.asr_config = config.transcription.remote_asr
        self.sample_rate = config.audio.sample_rate

        base_url = (self.asr_config.base_url or "").strip()
        if not base_url or "YOUR_ASR_HOST" in base_url:
            raise RuntimeError(
                "Remote ASR URL not configured. Set LOCAL_AI_ASR_BASE_URL in .env.local "
                "(see .env.example)."
            )

        client_config = ASRClientConfig(
            base_url=base_url,
            timeout=self.asr_config.timeout,
            model=self.asr_config.model,
            language=self.asr_config.language,
        )
        self._client = ASRClient(client_config)
        self._client_config = client_config

        logger.info("RemoteASRTranscriber initialized: %s", base_url)

    def transcribe(self, audio_data: np.ndarray) -> str:
        start_time = time.time()
        duration_seconds = len(audio_data) / self.sample_rate
        logger.info(
            "Remote ASR transcribe: %s samples (%.1fs)",
            len(audio_data),
            duration_seconds,
        )

        try:
            wav_bytes = self._audio_to_wav_bytes(audio_data)
            text = transcribe_wav_bytes(
                wav_bytes,
                config=self._client_config,
            )
            elapsed = time.time() - start_time
            logger.info(
                "Remote ASR done in %.2fs, %s chars",
                elapsed,
                len(text),
            )
            return text
        except requests.exceptions.ConnectionError as e:
            logger.error("ASR connection failed: %s", e)
            raise RuntimeError(
                "Cannot reach remote ASR. Check Tailscale and LOCAL_AI_ASR_BASE_URL."
            ) from e
        except requests.exceptions.Timeout as e:
            logger.error("ASR timeout: %s", e)
            raise RuntimeError("Remote ASR request timed out.") from e
        except Exception as e:
            logger.error("Remote ASR error: %s", e)
            raise RuntimeError(f"Remote ASR transcription failed: {e}") from e

    def _audio_to_wav_bytes(self, audio_data: np.ndarray) -> bytes:
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        max_val = max(abs(float(audio_data.max())), abs(float(audio_data.min())))
        if max_val > 1.0:
            audio_data = audio_data / max_val
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, self.sample_rate, format="WAV")
        return buffer.getvalue()
