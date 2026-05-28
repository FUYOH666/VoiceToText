"""
Абстракция движка транскрипции
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
        
        # Выбор движка
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
            from .remote_asr_engine import RemoteASRTranscriber

            self.engine = RemoteASRTranscriber(config)
            logger.info("Используется движок: Remote ASR (TailScale)")
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

