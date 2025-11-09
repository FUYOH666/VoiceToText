"""
Обработка аудио данных для VTTv2
"""
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Обработка аудио данных"""
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
        """
        Нормализация аудио данных
        
        Args:
            audio_data: Входные аудио данные
        
        Returns:
            Нормализованные аудио данные
        """
        if len(audio_data) == 0:
            return audio_data
        
        # Нормализация к диапазону [-1, 1]
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val
        
        return audio_data
    
    @staticmethod
    def validate_audio(
        audio_data: np.ndarray,
        expected_sample_rate: int = 16000,
        expected_channels: int = 1
    ) -> bool:
        """
        Валидация формата аудио
        
        Args:
            audio_data: Аудио данные
            expected_sample_rate: Ожидаемая частота дискретизации
            expected_channels: Ожидаемое количество каналов
        
        Returns:
            True если формат корректен
        """
        if audio_data is None or len(audio_data) == 0:
            logger.error("Пустые аудио данные")
            return False
        
        # Проверка моно канала
        if len(audio_data.shape) > 1 and audio_data.shape[1] != 1:
            logger.warning(f"Ожидается моно канал, получено: {audio_data.shape}")
            return False
        
        return True
    
    @staticmethod
    def prepare_for_whisper(audio_data: np.ndarray) -> np.ndarray:
        """
        Подготовка аудио данных для whisper.cpp
        
        Args:
            audio_data: Входные аудио данные
        
        Returns:
            Подготовленные аудио данные
        """
        # Нормализация
        audio_data = AudioProcessor.normalize_audio(audio_data)
        
        # Конвертация в моно если нужно
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Конвертация в float32
        audio_data = audio_data.astype(np.float32)
        
        return audio_data

