"""
Абстракция движка транскрипции.
Ленивые импорты — при remote_asr не загружаем MLX/whisper (экономия ~6 GB RAM).
"""
import logging
import numpy as np
from typing import Protocol

logger = logging.getLogger(__name__)


class TranscriptionEngine(Protocol):
    """Протокол для движка транскрипции"""

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Транскрибация аудио"""
        ...


class TranscriptionEngineWrapper:
    """Обертка для движка транскрипции"""

    def __init__(self, config):
        """
        Инициализация движка транскрипции

        Args:
            config: Конфигурация приложения
        """
        self.config = config
        engine_type = config.transcription.engine

        if engine_type == "whisper_cpp":
            from .whisper_cpp import WhisperCppTranscriber
            self.engine = WhisperCppTranscriber(config)
            logger.info("Используется движок: whisper.cpp")
        elif engine_type == "mlx_whisper":
            from .mlx_engine import MLXWhisperTranscriber
            self.engine = MLXWhisperTranscriber(config)
            logger.info("Используется движок: MLX Whisper (Apple Silicon)")
        elif engine_type == "remote_asr":
            from .remote_asr import RemoteASRTranscriber
            self.engine = RemoteASRTranscriber(config)
            logger.info("Используется движок: Remote ASR (Tailscale)")
        elif engine_type == "local_stt":
            from .local_stt import LocalSTTTranscriber
            self.engine = LocalSTTTranscriber(config)
            logger.info("Используется движок: Local STT HTTP (loopback)")
        else:
            raise ValueError(f"Неизвестный движок: {engine_type}")
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Транскрибация аудио данных
        
        Args:
            audio_data: numpy array с аудио данными
        
        Returns:
            Транскрибированный текст
        
        Raises:
            RuntimeError: При ошибке транскрипции
        """
        return self.engine.transcribe(audio_data)

    def transcribe_detailed(
        self,
        audio_data: np.ndarray,
        *,
        word_timestamps: bool = False,
    ) -> dict:
        """Segment-level result for HTTP verbose_json. Text-only engines get one span."""
        duration = float(len(audio_data) / 16000) if len(audio_data) else 0.0
        engine = self.engine
        if hasattr(engine, "transcribe_detailed"):
            payload = engine.transcribe_detailed(
                audio_data, word_timestamps=word_timestamps
            )
            payload.setdefault("duration", duration)
            payload.setdefault("segments", [])
            payload.setdefault("text", "")
            return payload
        text = engine.transcribe(audio_data)
        logger.info("Engine has no transcribe_detailed; one synthetic segment")
        return {
            "text": text or "",
            "language": None,
            "duration": duration,
            "segments": (
                [{"id": 0, "start": 0.0, "end": duration, "text": text}]
                if text
                else []
            ),
        }

