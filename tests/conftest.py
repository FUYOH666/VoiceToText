"""
Общие фикстуры и конфигурация для тестов VTTv2
"""
import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Добавляем пакет vtt2 в путь для импортов (чтобы работали from config.loader, from utils.logger и т.д.)
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "vtt2"))

# Мокируем mlx_whisper модуль ДО импорта других модулей если он не установлен
try:
    import mlx_whisper
except ImportError:
    from unittest.mock import MagicMock as MockModule
    mlx_whisper_mock = MockModule()
    mlx_whisper_mock.transcribe = lambda *args, **kwargs: {"text": "test"}
    sys.modules['mlx_whisper'] = mlx_whisper_mock


@pytest.fixture
def temp_config_file():
    """Создает временный файл конфигурации"""
    config_data = {
        "app": {
            "version": "1.0.0",
            "name": "VTTv2"
        },
        "transcription": {
            "engine": "mlx_whisper",
            "mlx_whisper": {
                "model_name": "mlx-community/whisper-medium",
                "language": "ru"
            }
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1
        },
        "ui": {
            "auto_paste_enabled": True,
            "hotkey": "option+space"
        },
        "menu_bar": {
            "icon_idle": "🎤",
            "icon_recording": "🔴",
            "show_status": True
        },
        "text_processing": {
            "enabled": False,
            "strip_whisper_tail_artifacts": True,
            "whisper_artifact_languages": ["ru", "en"],
        },
        "performance": {
            "use_neural_engine": True,
            "max_concurrent_tasks": 1,
            "memory_limit_mb": 4096
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Удаляем временный файл после теста
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def project_root():
    """Возвращает корневую директорию проекта"""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_audio_data():
    """Создает тестовые аудио данные"""
    import numpy as np
    # Генерируем синусоиду для тестирования
    sample_rate = 16000
    duration = 1.0  # секунда
    frequency = 440  # Hz
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    return audio.astype(np.float32)

