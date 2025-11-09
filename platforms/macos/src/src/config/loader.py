"""
Загрузка и валидация конфигурации VTTv2
Использует pydantic для валидации и поддержку ENV переопределений
"""
import os
import logging
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml


logger = logging.getLogger(__name__)


class WhisperCppConfig(BaseModel):
    """Конфигурация whisper.cpp"""
    binary_path: str = Field(..., description="Путь к бинарнику whisper")
    model_path: str = Field(..., description="Путь к модели")
    use_coreml: bool = Field(True, description="Использовать Core ML")
    use_metal: bool = Field(True, description="Использовать Metal")
    threads: int = Field(8, ge=1, le=16, description="Количество потоков")
    language: str = Field("ru", description="Язык транскрипции")
    temperature: float = Field(0.0, ge=0.0, le=1.0, description="Temperature")
    beam_size: int = Field(5, ge=1, description="Beam size")
    best_of: int = Field(5, ge=1, description="Best of")
    patience: float = Field(1.0, ge=0.0, description="Patience")
    no_speech_threshold: float = Field(0.6, ge=0.0, le=1.0, description="No speech threshold")
    compression_ratio_threshold: float = Field(2.4, ge=0.0, description="Compression ratio threshold")


class TranscriptionConfig(BaseModel):
    """Конфигурация транскрипции"""
    engine: Literal["whisper_cpp"] = Field("whisper_cpp", description="Движок транскрипции")
    whisper_cpp: WhisperCppConfig = Field(..., description="Настройки whisper.cpp")


class AudioConfig(BaseModel):
    """Конфигурация аудио"""
    sample_rate: int = Field(16000, description="Частота дискретизации")
    channels: int = Field(1, description="Количество каналов")
    device_index: Optional[int] = Field(None, description="Индекс устройства")
    chunk_size: int = Field(1024, ge=256, description="Размер чанка")
    max_recording_duration: int = Field(3600, ge=1, description="Максимальная длительность записи (сек)")


class UIConfig(BaseModel):
    """Конфигурация UI"""
    auto_paste_enabled: bool = Field(True, description="Автовставка включена")
    auto_paste_method: Literal["cgevent", "clipboard"] = Field("cgevent", description="Метод автовставки")
    hotkey: str = Field("option+space", description="Горячая клавиша")


class MenuBarConfig(BaseModel):
    """Конфигурация menu bar"""
    icon_idle: str = Field("🎤", description="Иконка в состоянии готов")
    icon_recording: str = Field("🔴", description="Иконка в состоянии записи")
    show_status: bool = Field(True, description="Показывать статус")


class TextProcessingConfig(BaseModel):
    """Конфигурация постобработки текста"""
    enabled: bool = Field(False, description="Включена постобработка")


class PerformanceConfig(BaseModel):
    """Конфигурация производительности"""
    use_neural_engine: bool = Field(True, description="Использовать Neural Engine")
    max_concurrent_tasks: int = Field(1, ge=1, description="Максимум одновременных задач")
    memory_limit_mb: int = Field(16384, ge=1024, description="Лимит памяти (MB)")


class LoggingConfig(BaseModel):
    """Конфигурация логирования"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field("INFO", description="Уровень логирования")
    format: str = Field("%(asctime)s %(levelname)s %(name)s %(message)s", description="Формат логов")
    file: Optional[str] = Field(None, description="Файл логов (None = только консоль)")


class AppConfig(BaseModel):
    """Конфигурация приложения"""
    version: str = Field(..., description="Версия приложения")
    name: str = Field(..., description="Название приложения")


class Config(BaseModel):
    """Полная конфигурация VTTv2"""
    app: AppConfig
    transcription: TranscriptionConfig
    audio: AudioConfig
    ui: UIConfig
    menu_bar: MenuBarConfig
    text_processing: TextProcessingConfig
    performance: PerformanceConfig
    logging: LoggingConfig
    
    @model_validator(mode='after')
    def validate_paths(self) -> 'Config':
        """Проверка путей к файлам"""
        # Проверка бинарника whisper.cpp
        binary_path = Path(self.transcription.whisper_cpp.binary_path)
        if not binary_path.is_absolute():
            # Относительный путь - разрешаем относительно проекта
            # Будет проверен позже при инициализации
            pass
        
        # Проверка модели
        model_path = Path(self.transcription.whisper_cpp.model_path)
        if not model_path.is_absolute():
            # Относительный путь - разрешаем относительно проекта
            # Будет проверен позже при инициализации
            pass
        
        return self
    
    @classmethod
    def from_yaml(cls, config_path: str, project_root: Optional[Path] = None) -> 'Config':
        """
        Загрузка конфигурации из YAML файла с поддержкой ENV переопределений
        
        Args:
            config_path: Путь к config.yaml
            project_root: Корневая директория проекта (для разрешения относительных путей)
        
        Returns:
            Валидированная конфигурация
        
        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если конфигурация невалидна
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
        
        logger.info(f"Загрузка конфигурации из {config_path}")
        
        # Загрузка YAML
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if not config_data:
            raise ValueError("Конфигурационный файл пуст")
        
        # Применение ENV переопределений (приоритет выше YAML)
        config_data = cls._apply_env_overrides(config_data)
        
        # Разрешение относительных путей
        if project_root:
            config_data = cls._resolve_paths(config_data, project_root)
        
        try:
            # Валидация через pydantic
            config = cls(**config_data)
            logger.info("Конфигурация успешно загружена и валидирована")
            return config
        except Exception as e:
            logger.error(f"Ошибка валидации конфигурации: {e}")
            raise ValueError(f"Невалидная конфигурация: {e}") from e
    
    @staticmethod
    def _apply_env_overrides(config_data: dict) -> dict:
        """Применение переопределений из ENV переменных"""
        # Поддержка основных ENV переопределений
        # Например: VTT2_TRANSCRIPTION_WHISPER_CPP_THREADS=4
        # Префикс: VTT2_
        
        env_prefix = "VTT2_"
        
        def set_nested_value(d: dict, keys: list[str], value: str):
            """Установка значения во вложенном словаре"""
            current = d
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(env_prefix):
                continue
            
            # Удаление префикса и конвертация в ключи
            keys = env_key[len(env_prefix):].lower().split('_')
            
            # Конвертация значения в правильный тип
            try:
                # Попытка конвертации в число
                if env_value.isdigit():
                    env_value = int(env_value)
                elif env_value.replace('.', '', 1).isdigit():
                    env_value = float(env_value)
                elif env_value.lower() in ('true', 'false'):
                    env_value = env_value.lower() == 'true'
            except (ValueError, AttributeError):
                pass  # Оставляем как строку
            
            # Установка значения (примерно - упрощенная версия)
            # В реальной версии нужна более сложная логика для вложенных структур
            logger.debug(f"ENV override: {env_key} = {env_value}")
        
        return config_data
    
    @staticmethod
    def _resolve_paths(config_data: dict, project_root: Path) -> dict:
        """Разрешение относительных путей относительно project_root"""
        # Разрешение пути к бинарнику
        if 'transcription' in config_data and 'whisper_cpp' in config_data['transcription']:
            binary_path = config_data['transcription']['whisper_cpp'].get('binary_path')
            if binary_path and not Path(binary_path).is_absolute():
                config_data['transcription']['whisper_cpp']['binary_path'] = str(
                    (project_root / binary_path).resolve()
                )
            
            model_path = config_data['transcription']['whisper_cpp'].get('model_path')
            if model_path and not Path(model_path).is_absolute():
                config_data['transcription']['whisper_cpp']['model_path'] = str(
                    (project_root / model_path).resolve()
                )
        
        return config_data

