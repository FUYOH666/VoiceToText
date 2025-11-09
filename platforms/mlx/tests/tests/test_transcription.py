"""
Тесты для транскрипции (с моками MLX Whisper)
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMLXWhisperTranscription:
    """Тесты транскрипции через MLX Whisper (с моками)"""
    
    @patch('mlx_whisper.transcribe')
    def test_transcribe_success(self, mock_transcribe):
        """Тест успешной транскрипции"""
        from src.transcription.mlx_engine import MLXWhisperTranscriber
        
        # Мокируем результат транскрипции
        mock_transcribe.return_value = {
            "text": "Привет мир",
            "segments": [{"text": "Привет мир"}]
        }
        
        # Создаем мок конфигурации
        mock_config = MagicMock()
        mock_config.transcription.mlx_whisper.model_name = "mlx-community/whisper-medium"
        mock_config.transcription.mlx_whisper.language = "ru"
        mock_config.transcription.mlx_whisper.temperature = 0.0
        mock_config.transcription.mlx_whisper.beam_size = 5
        mock_config.transcription.mlx_whisper.best_of = 5
        mock_config.transcription.mlx_whisper.no_speech_threshold = 0.6
        mock_config.transcription.mlx_whisper.compression_ratio_threshold = 2.4
        
        # Мокируем проверки зависимостей
        with patch.object(MLXWhisperTranscriber, '_check_dependencies'):
            with patch.object(MLXWhisperTranscriber, '_check_model_cache'):
                # Создаем транскрибатор
                transcriber = MLXWhisperTranscriber(mock_config)
                
                # Тестовые аудио данные
                audio_data = np.random.randn(16000).astype(np.float32)
                
                # Выполняем транскрипцию
                result = transcriber.transcribe(audio_data)
                
                # Проверяем результат
                assert result == "Привет мир"
                mock_transcribe.assert_called_once()
    
    @patch('mlx_whisper.transcribe')
    def test_transcribe_empty_result(self, mock_transcribe):
        """Тест обработки пустого результата транскрипции"""
        from src.transcription.mlx_engine import MLXWhisperTranscriber
        
        # Мокируем пустой результат
        mock_transcribe.return_value = {"text": ""}
        
        mock_config = MagicMock()
        mock_config.transcription.mlx_whisper.model_name = "mlx-community/whisper-medium"
        mock_config.transcription.mlx_whisper.language = "ru"
        mock_config.transcription.mlx_whisper.temperature = 0.0
        mock_config.transcription.mlx_whisper.beam_size = 5
        mock_config.transcription.mlx_whisper.best_of = 5
        mock_config.transcription.mlx_whisper.no_speech_threshold = 0.6
        mock_config.transcription.mlx_whisper.compression_ratio_threshold = 2.4
        
        with patch.object(MLXWhisperTranscriber, '_check_dependencies'):
            with patch.object(MLXWhisperTranscriber, '_check_model_cache'):
                transcriber = MLXWhisperTranscriber(mock_config)
                audio_data = np.random.randn(16000).astype(np.float32)
                
                result = transcriber.transcribe(audio_data)
                
                # Должен вернуть пустую строку
                assert result == ""
    
    @patch('mlx_whisper.transcribe')
    def test_transcribe_error_handling(self, mock_transcribe):
        """Тест обработки ошибок транскрипции"""
        from src.transcription.mlx_engine import MLXWhisperTranscriber
        
        # Мокируем ошибку
        mock_transcribe.side_effect = Exception("Ошибка транскрипции")
        
        mock_config = MagicMock()
        mock_config.transcription.mlx_whisper.model_name = "mlx-community/whisper-medium"
        mock_config.transcription.mlx_whisper.language = "ru"
        mock_config.transcription.mlx_whisper.temperature = 0.0
        mock_config.transcription.mlx_whisper.beam_size = 5
        mock_config.transcription.mlx_whisper.best_of = 5
        mock_config.transcription.mlx_whisper.no_speech_threshold = 0.6
        mock_config.transcription.mlx_whisper.compression_ratio_threshold = 2.4
        
        with patch.object(MLXWhisperTranscriber, '_check_dependencies'):
            with patch.object(MLXWhisperTranscriber, '_check_model_cache'):
                transcriber = MLXWhisperTranscriber(mock_config)
                audio_data = np.random.randn(16000).astype(np.float32)
                
                # Должно выбросить RuntimeError
                with pytest.raises(RuntimeError, match="Ошибка транскрипции MLX"):
                    transcriber.transcribe(audio_data)
    
    @patch('mlx_whisper.transcribe')
    def test_transcribe_audio_normalization(self, mock_transcribe):
        """Тест нормализации аудио перед транскрипцией"""
        from src.transcription.mlx_engine import MLXWhisperTranscriber
        
        mock_transcribe.return_value = {"text": "test"}
        
        mock_config = MagicMock()
        mock_config.transcription.mlx_whisper.model_name = "mlx-community/whisper-medium"
        mock_config.transcription.mlx_whisper.language = "ru"
        mock_config.transcription.mlx_whisper.temperature = 0.0
        mock_config.transcription.mlx_whisper.beam_size = 5
        mock_config.transcription.mlx_whisper.best_of = 5
        mock_config.transcription.mlx_whisper.no_speech_threshold = 0.6
        mock_config.transcription.mlx_whisper.compression_ratio_threshold = 2.4
        
        with patch.object(MLXWhisperTranscriber, '_check_dependencies'):
            with patch.object(MLXWhisperTranscriber, '_check_model_cache'):
                transcriber = MLXWhisperTranscriber(mock_config)
                
                # Аудио с большими значениями (должно нормализоваться)
                audio_data = (np.random.randn(16000) * 10).astype(np.float32)
                
                transcriber.transcribe(audio_data)
                
                # Проверяем что whisper.transcribe был вызван
                call_args = mock_transcribe.call_args
                normalized_audio = call_args[0][0]  # Первый аргумент
                
                # Проверяем что аудио нормализовано (в диапазоне [-1, 1])
                assert np.all(normalized_audio >= -1.0)
                assert np.all(normalized_audio <= 1.0)
                assert normalized_audio.dtype == np.float32


class TestTranscriptionEngineWrapper:
    """Тесты обертки для движка транскрипции"""
    
    def test_engine_selection_mlx(self):
        """Тест выбора движка MLX Whisper"""
        from src.transcription.engine import TranscriptionEngineWrapper
        from src.transcription.mlx_engine import MLXWhisperTranscriber
        
        mock_config = MagicMock()
        mock_config.transcription.engine = "mlx_whisper"
        mock_config.transcription.mlx_whisper.model_name = "mlx-community/whisper-medium"
        mock_config.transcription.mlx_whisper.language = "ru"
        mock_config.transcription.mlx_whisper.temperature = 0.0
        mock_config.transcription.mlx_whisper.beam_size = 5
        mock_config.transcription.mlx_whisper.best_of = 5
        mock_config.transcription.mlx_whisper.no_speech_threshold = 0.6
        mock_config.transcription.mlx_whisper.compression_ratio_threshold = 2.4
        
        with patch.object(MLXWhisperTranscriber, '_check_dependencies'):
            with patch.object(MLXWhisperTranscriber, '_check_model_cache'):
                wrapper = TranscriptionEngineWrapper(mock_config)
                assert wrapper.engine is not None
    
    def test_engine_selection_invalid(self):
        """Тест выбора невалидного движка"""
        from src.transcription.engine import TranscriptionEngineWrapper
        
        mock_config = MagicMock()
        mock_config.transcription.engine = "invalid_engine"
        
        with pytest.raises(ValueError, match="Неизвестный движок"):
            TranscriptionEngineWrapper(mock_config)

