"""
Загрузка и валидация конфигурации VTTv2
Использует pydantic для валидации и поддержку ENV переопределений
"""
import os
import logging
from pathlib import Path
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml


logger = logging.getLogger(__name__)


class MLXWhisperConfig(BaseModel):
    """Конфигурация MLX Whisper"""
    model_name: str = Field("mlx-community/whisper-medium", description="Название модели MLX (например, mlx-community/whisper-medium)")
    language: Optional[str] = Field("ru", description="Язык транскрипции: 'ru' (default), 'auto' для автоопределения, или код языка ('en', 'zh', 'ja' и т.д.)")
    temperature: float = Field(0.0, ge=0.0, le=1.0, description="Temperature")
    beam_size: int = Field(5, ge=1, description="Beam size")
    best_of: int = Field(5, ge=1, description="Best of")
    no_speech_threshold: float = Field(0.6, ge=0.0, le=1.0, description="No speech threshold")
    compression_ratio_threshold: float = Field(2.4, ge=0.0, description="Compression ratio threshold")
    # Параметры для обработки длинных записей
    chunk_size_seconds: int = Field(30, ge=10, le=300, description="Размер чанка для обработки длинных записей (секунды)")
    chunk_overlap_seconds: int = Field(2, ge=0, le=10, description="Перекрытие между чанками (секунды)")
    batch_size: int = Field(6, ge=1, le=24, description="Размер батча для параллельной обработки чанков")


class RemoteASRConfig(BaseModel):
    """Конфигурация удалённого ASR (LocalAI-compatible, доступ через Tailscale)"""
    host: str = Field(
        "localhost",
        description="Хост ASR (Tailscale IP или localhost)",
    )
    port: int = Field(8001, ge=1, le=65535, description="Порт ASR-сервера")
    path: str = Field(
        "/v1/audio/transcriptions",
        description="Путь к эндпоинту (LocalAI: /v1/audio/transcriptions)",
    )
    model: str = Field(
        "cstr/whisper-large-v3-turbo-int8_float32",
        description="Модель ASR на сервере",
    )
    timeout_seconds: int = Field(60, ge=5, le=300, description="Таймаут запроса (секунды)")


class LocalSTTConfig(BaseModel):
    """Клиент к локальному STT HTTP API (menubar → loopback)"""
    base_url: str = Field(
        "http://127.0.0.1:8765",
        description="Базовый URL локального STT (только loopback)",
    )
    path: str = Field(
        "/v1/audio/transcriptions",
        description="Путь к эндпоинту транскрипции",
    )
    timeout_seconds: int = Field(
        600, ge=5, le=3600, description="Таймаут запроса (секунды)"
    )
    warmup_wait_seconds: int = Field(
        180,
        ge=0,
        le=3600,
        description="Сколько ждать on-demand load модели при 503 (idle unload)",
    )


class STTServerConfig(BaseModel):
    """Локальный OpenAI-compatible STT HTTP сервер (владелец модели)"""
    host: str = Field("127.0.0.1", description="Bind host (только loopback)")
    port: int = Field(8765, ge=1, le=65535, description="Порт STT API")
    max_upload_mb: int = Field(25, ge=1, le=200, description="Лимит размера файла (MB)")
    request_timeout_seconds: int = Field(
        600, ge=30, le=3600, description="Таймаут обработки одного запроса"
    )
    engine: Literal["mlx_whisper", "whisper_cpp"] = Field(
        "mlx_whisper",
        description="Движок, который грузит STT-сервер (не local_stt/remote_asr)",
    )
    preload_on_start: bool = Field(
        True,
        description="Загружать модель при старте процесса (false = on-demand)",
    )
    idle_unload_seconds: int = Field(
        0,
        ge=0,
        le=86400,
        description="Выгрузить модель после N секунд без запросов (0 = никогда)",
    )


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
    engine: Literal["whisper_cpp", "mlx_whisper", "remote_asr", "local_stt"] = Field(
        "local_stt", description="Движок транскрипции (menubar: local_stt → HTTP)"
    )
    whisper_cpp: Optional[WhisperCppConfig] = Field(None, description="Настройки whisper.cpp")
    mlx_whisper: Optional[MLXWhisperConfig] = Field(None, description="Настройки MLX Whisper")
    remote_asr: Optional[RemoteASRConfig] = Field(None, description="Настройки удалённого ASR")
    local_stt: Optional[LocalSTTConfig] = Field(None, description="Клиент локального STT HTTP")

    @model_validator(mode='after')
    def validate_engine_config(self):
        """Проверка что конфигурация движка соответствует выбранному движку"""
        if self.engine == "whisper_cpp" and not self.whisper_cpp:
            raise ValueError("whisper_cpp движок требует whisper_cpp конфигурацию")
        if self.engine == "mlx_whisper" and not self.mlx_whisper:
            self.mlx_whisper = MLXWhisperConfig()
        if self.engine == "remote_asr" and not self.remote_asr:
            self.remote_asr = RemoteASRConfig()
        if self.engine == "local_stt" and not self.local_stt:
            self.local_stt = LocalSTTConfig()
        # MLX конфиг нужен STT-серверу даже когда menubar на local_stt
        if self.mlx_whisper is None:
            self.mlx_whisper = MLXWhisperConfig()
        return self


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
    strip_whisper_tail_artifacts: bool = Field(
        True,
        description="Удалять типичные хвостовые фразы Whisper перед вставкой",
    )
    whisper_artifact_languages: List[Literal["ru", "en"]] = Field(
        default_factory=lambda: ["ru", "en"],
        description="Языки списков артефактов (ru/en)",
    )


class PerformanceConfig(BaseModel):
    """Конфигурация производительности"""
    use_neural_engine: bool = Field(True, description="Использовать Neural Engine")
    max_concurrent_tasks: int = Field(1, ge=1, description="Максимум одновременных задач")
    memory_limit_mb: int = Field(16384, ge=1024, description="Лимит памяти (MB)")
    auto_cleanup_enabled: bool = Field(True, description="Автоматическая очистка памяти")
    cleanup_threshold_percent: int = Field(75, ge=50, le=95, description="Порог для запуска очистки (% от лимита)")
    periodic_cleanup_interval: int = Field(10, ge=1, description="Очистка памяти каждые N транскрипций")


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
    stt_server: STTServerConfig = Field(default_factory=STTServerConfig)

    @model_validator(mode='after')
    def validate_paths(self) -> 'Config':
        """Проверка путей к файлам и bind STT"""
        if self.stt_server.host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(
                "stt_server.host должен быть loopback (127.0.0.1 / localhost / ::1); "
                f"получено: {self.stt_server.host}"
            )
        # Проверка бинарника whisper.cpp (только если используется whisper_cpp)
        if self.transcription.whisper_cpp:
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
            
            set_nested_value(config_data, keys, env_value)
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

