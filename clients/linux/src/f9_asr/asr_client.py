"""ASR API client — delegates to shared vtt_asr_client."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from f9_asr.config import ASRConfig

logger = logging.getLogger(__name__)

# Repository root: .../clients/linux/src/f9_asr/asr_client.py → 5 levels up
_REPO_SRC = Path(__file__).resolve().parents[4] / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from vtt_asr_client.client import ASRClient as _SharedClient
from vtt_asr_client.client import ASRClientConfig


class ASRClient:
    """F9 wrapper around shared OpenAI-compatible ASR client."""

    def __init__(self, config: ASRConfig):
        self.config = config
        lang = config.language
        self._inner = _SharedClient(
            ASRClientConfig(
                base_url=config.base_url.rstrip("/"),
                timeout=config.timeout,
                model="whisper",
                language=lang,
                transcription_endpoint=config.transcription_endpoint,
                response_format=config.response_format,
            )
        )

    def transcribe(self, audio_file: Path) -> str:
        logger.info("Transcribing %s via %s", audio_file, self.config.base_url)
        return self._inner.transcribe_file(audio_file)

    def health_check(self) -> bool:
        return self._inner.healthz()
