"""
Тесты для обработки аудио данных VTTv2
"""
import pytest
import numpy as np
from src.audio.processor import AudioProcessor


class TestAudioProcessor:
    """Тесты обработки аудио данных"""
    
    def test_normalize_audio_basic(self):
        """Тест базовой нормализации аудио"""
        # Создаем тестовые данные вне диапазона [-1, 1]
        audio_data = np.array([2.0, -2.0, 1.5, -1.5], dtype=np.float32)
        
        normalized = AudioProcessor.normalize_audio(audio_data)
        
        # Проверяем что значения в диапазоне [-1, 1]
        assert np.all(normalized >= -1.0)
        assert np.all(normalized <= 1.0)
        # Проверяем что максимум равен 1.0 или -1.0
        assert abs(normalized.max()) == 1.0 or abs(normalized.min()) == 1.0
    
    def test_normalize_audio_already_normalized(self):
        """Тест нормализации уже нормализованных данных"""
        audio_data = np.array([0.5, -0.5, 0.3, -0.3], dtype=np.float32)
        
        normalized = AudioProcessor.normalize_audio(audio_data)
        
        # Должно остаться примерно тем же (или нормализоваться к максимуму)
        assert len(normalized) == len(audio_data)
    
    def test_normalize_audio_empty(self):
        """Тест нормализации пустых данных"""
        audio_data = np.array([], dtype=np.float32)
        
        normalized = AudioProcessor.normalize_audio(audio_data)
        
        assert len(normalized) == 0
    
    def test_normalize_audio_zeros(self):
        """Тест нормализации нулевых данных"""
        audio_data = np.zeros(100, dtype=np.float32)
        
        normalized = AudioProcessor.normalize_audio(audio_data)
        
        assert len(normalized) == 100
        assert np.all(normalized == 0)
    
    def test_validate_audio_valid(self, sample_audio_data):
        """Тест валидации корректных аудио данных"""
        result = AudioProcessor.validate_audio(sample_audio_data)
        assert result is True
    
    def test_validate_audio_empty(self):
        """Тест валидации пустых данных"""
        audio_data = np.array([], dtype=np.float32)
        
        result = AudioProcessor.validate_audio(audio_data)
        assert result is False
    
    def test_validate_audio_none(self):
        """Тест валидации None данных"""
        result = AudioProcessor.validate_audio(None)
        assert result is False
    
    def test_prepare_for_whisper_basic(self, sample_audio_data):
        """Тест базовой подготовки аудио для Whisper"""
        prepared = AudioProcessor.prepare_for_whisper(sample_audio_data)
        
        # Проверяем что данные в float32
        assert prepared.dtype == np.float32
        # Проверяем что данные одномерные (моно)
        assert len(prepared.shape) == 1
        # Проверяем что нормализованы
        assert np.all(prepared >= -1.0)
        assert np.all(prepared <= 1.0)
    
    def test_prepare_for_whisper_stereo(self):
        """Тест подготовки стерео аудио (конвертация в моно)"""
        # Создаем стерео данные (2 канала)
        stereo_audio = np.array([
            [1.0, 0.5],
            [0.5, 1.0],
            [0.3, 0.7]
        ], dtype=np.float32)
        
        prepared = AudioProcessor.prepare_for_whisper(stereo_audio)
        
        # Должно быть конвертировано в моно
        assert len(prepared.shape) == 1
        assert prepared.dtype == np.float32
    
    def test_prepare_for_whisper_large_values(self):
        """Тест подготовки аудио с большими значениями"""
        # Данные вне диапазона [-1, 1]
        audio_data = np.array([10.0, -10.0, 5.0, -5.0], dtype=np.float32)
        
        prepared = AudioProcessor.prepare_for_whisper(audio_data)
        
        # Должно быть нормализовано
        assert np.all(prepared >= -1.0)
        assert np.all(prepared <= 1.0)
        assert prepared.dtype == np.float32

