"""
Загрузка и валидация конфигурации VTTv2
Слои: config/base.yaml + config/profiles/<profile>.yaml + ENV + .env.local
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field, PrivateAttr, model_validator
import yaml

from config.merge import deep_merge

logger = logging.getLogger(__name__)

MAC_PROFILES = (
    "mac-m1-local",
    "mac-m1-remote",
    "mac-m4-local",
    "mac-m4-remote",
)
DEFAULT_PROFILE = "mac-m1-local"
PLACEHOLDER_ASR_URL = "http://YOUR_ASR_HOST:8001"


class MLXWhisperConfig(BaseModel):
    """Конфигурация MLX Whisper"""
    model_name: str = Field("mlx-community/whisper-medium", description="Название модели MLX (например, mlx-community/whisper-medium)")
    language: Optional[str] = Field("auto", description="Язык транскрипции: 'auto' для автоопределения, или код языка ('ru', 'en', 'zh', 'ja' и т.д.)")
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
    """Конфигурация удаленного ASR сервиса"""
    base_url: str = Field(
        default="",
        description="URL ASR (LOCAL_AI_ASR_BASE_URL или .env.local)",
    )
    timeout: int = Field(
        60,
        ge=10,
        le=300,
        description="Таймаут запроса в секундах (LOCAL_AI_ASR_TIMEOUT)",
    )
    model: str = Field(
        "cstr/whisper-large-v3-turbo-int8_float32",
        description="Модель ASR",
    )
    language: Optional[str] = Field(
        "auto",
        description="Язык: 'auto' для автоопределения, или 'ru', 'en' (LOCAL_AI_ASR_DEFAULT_LANGUAGE)",
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
    engine: Literal["whisper_cpp", "mlx_whisper", "remote_asr"] = Field(
        "mlx_whisper", description="Движок транскрипции"
    )
    whisper_cpp: Optional[WhisperCppConfig] = Field(None, description="Настройки whisper.cpp")
    mlx_whisper: Optional[MLXWhisperConfig] = Field(None, description="Настройки MLX Whisper")
    remote_asr: Optional[RemoteASRConfig] = Field(None, description="Настройки удаленного ASR")

    @model_validator(mode='after')
    def validate_engine_config(self):
        """Проверка что конфигурация движка соответствует выбранному движку"""
        if self.engine == "whisper_cpp" and not self.whisper_cpp:
            raise ValueError("whisper_cpp движок требует whisper_cpp конфигурацию")
        if self.engine == "mlx_whisper" and not self.mlx_whisper:
            self.mlx_whisper = MLXWhisperConfig()
        if self.engine == "remote_asr" and not self.remote_asr:
            self.remote_asr = RemoteASRConfig()
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
    icon_processing: str = Field("⏳", description="Иконка при остановке записи и транскрипции")
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
    _active_profile: str = PrivateAttr(default=DEFAULT_PROFILE)

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
    def resolve_profile_name(
        cls,
        profile: Optional[str] = None,
        config_path: Optional[Path] = None,
    ) -> str:
        """Profile: CLI/env > config.yaml active_profile > default."""
        if profile:
            return profile
        env_profile = os.getenv("VTT2_PROFILE")
        if env_profile:
            return env_profile
        if config_path and config_path.is_file():
            with open(config_path, encoding="utf-8") as f:
                root = yaml.safe_load(f) or {}
            if isinstance(root, dict) and root.get("active_profile"):
                return str(root["active_profile"])
        return DEFAULT_PROFILE

    @classmethod
    def from_yaml(
        cls,
        config_path: str,
        project_root: Optional[Path] = None,
        profile: Optional[str] = None,
    ) -> "Config":
        """
        Загрузка конфигурации: layered profiles или legacy full config.yaml.
        """
        if project_root is None:
            project_root = Path(config_path).resolve().parent

        config_file = Path(config_path)
        if not config_file.is_absolute():
            config_file = project_root / config_file

        profile_name = cls.resolve_profile_name(profile, config_file)
        base_path = project_root / "config" / "base.yaml"
        profile_path = project_root / "config" / "profiles" / f"{profile_name}.yaml"
        root_config = (project_root / "config.yaml").resolve()

        if not config_file.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

        with open(config_file, encoding="utf-8") as f:
            file_data = yaml.safe_load(f) or {}

        use_layered = cls._should_use_layered(
            config_file.resolve(),
            root_config,
            file_data,
            profile,
            base_path,
            profile_path,
        )

        if use_layered:
            config_data, active = cls._load_layered(
                project_root, profile_name, base_path, profile_path
            )
            logger.info("Конфигурация: base + profile %s", active)
        else:
            logger.info("Загрузка legacy конфигурации из %s", config_path)
            config_data = file_data
            if config_data.get("active_profile") and not config_data.get("app"):
                raise ValueError(
                    f"Profile {config_data['active_profile']!r} requires "
                    f"config/base.yaml and config/profiles/"
                )
            active = "legacy"

        cls._load_env_file(project_root / ".env.local")
        config_data = cls._apply_env_overrides(config_data)
        config_data = cls._apply_local_ai_asr_env(config_data)

        if project_root:
            config_data = cls._resolve_paths(config_data, project_root)

        try:
            config = cls(**config_data)
            config._active_profile = active
            logger.info("Конфигурация успешно загружена (profile=%s)", active)
            return config
        except Exception as e:
            logger.error("Ошибка валидации конфигурации: %s", e)
            raise ValueError(f"Невалидная конфигурация: {e}") from e

    @property
    def active_profile(self) -> str:
        return self._active_profile

    @staticmethod
    def _should_use_layered(
        config_file: Path,
        root_config: Path,
        file_data: dict[str, Any],
        profile: Optional[str],
        base_path: Path,
        profile_path: Path,
    ) -> bool:
        if not base_path.is_file() or not profile_path.is_file():
            return False
        if profile or os.getenv("VTT2_PROFILE"):
            return config_file == root_config or "app" not in file_data
        if config_file != root_config:
            return False
        if "app" in file_data:
            return False
        return bool(file_data.get("active_profile"))

    @classmethod
    def _load_layered(
        cls,
        project_root: Path,
        profile_name: str,
        base_path: Path,
        profile_path: Path,
    ) -> tuple[dict[str, Any], str]:
        if profile_name not in MAC_PROFILES:
            raise ValueError(
                f"Unknown Mac profile {profile_name!r}; expected one of {MAC_PROFILES}"
            )
        with open(base_path, encoding="utf-8") as f:
            base_data = yaml.safe_load(f) or {}
        with open(profile_path, encoding="utf-8") as f:
            profile_data = yaml.safe_load(f) or {}
        return deep_merge(base_data, profile_data), profile_name

    @staticmethod
    def _load_env_file(path: Path) -> None:
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    
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
    def _apply_local_ai_asr_env(config_data: dict) -> dict:
        """Применение LOCAL_AI_ASR_* переменных окружения для remote_asr"""
        if "transcription" not in config_data:
            config_data["transcription"] = {}
        if "remote_asr" not in config_data["transcription"]:
            config_data["transcription"]["remote_asr"] = {}

        asr_env = {
            "LOCAL_AI_ASR_BASE_URL": "base_url",
            "LOCAL_AI_ASR_TIMEOUT": "timeout",
            "LOCAL_AI_ASR_DEFAULT_LANGUAGE": "language",
        }
        for env_key, config_key in asr_env.items():
            value = os.getenv(env_key)
            if value is not None:
                if config_key == "timeout":
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                config_data["transcription"]["remote_asr"][config_key] = value

        remote = config_data.get("transcription", {}).get("remote_asr", {})
        if config_data.get("transcription", {}).get("engine") == "remote_asr":
            url = remote.get("base_url", "")
            if not url or url == PLACEHOLDER_ASR_URL or "YOUR_ASR_HOST" in str(url):
                env_url = os.getenv("LOCAL_AI_ASR_BASE_URL", "").strip()
                if env_url:
                    config_data["transcription"]["remote_asr"]["base_url"] = env_url.rstrip("/")

        return config_data

    @staticmethod
    def remote_asr_url_configured(config_data: dict[str, Any]) -> bool:
        """True if remote ASR has a non-placeholder base URL."""
        engine = config_data.get("transcription", {}).get("engine")
        if engine != "remote_asr":
            return True
        url = (
            config_data.get("transcription", {})
            .get("remote_asr", {})
            .get("base_url", "")
        )
        if not url or "YOUR_ASR_HOST" in str(url):
            return bool(os.getenv("LOCAL_AI_ASR_BASE_URL", "").strip())
        return True
    
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

