"""Configuration management using Pydantic Settings."""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ASRConfig(BaseSettings):
    """ASR service configuration."""

    base_url: str = Field(default="http://localhost:8001", description="ASR service URL")
    transcription_endpoint: str = Field(
        default="/v1/audio/transcriptions", description="Transcription endpoint"
    )
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    language: Optional[str] = Field(
        default=None, description="Language code (None for auto-detection)"
    )
    response_format: str = Field(
        default="text", description="Response format: json, text, srt, verbose_json, vtt"
    )


class AudioConfig(BaseSettings):
    """Audio recording configuration."""

    sample_rate: int = Field(default=16000, ge=8000, le=48000, description="Sample rate in Hz")
    channels: int = Field(default=1, ge=1, le=2, description="Number of channels")
    format: str = Field(default="S16_LE", description="Audio format")
    temp_dir: str = Field(default="/tmp/f9-asr-recordings", description="Temporary directory")
    device: Optional[str] = Field(
        default=None,
        description="ALSA capture device (e.g. plughw:CARD=Generic_1,DEV=0). None = system default",
    )
    max_duration: int = Field(
        default=0, ge=0, description="Max recording duration in seconds (0 = unlimited)"
    )
    cleanup_max_age_hours: int = Field(
        default=24, ge=0, description="Auto-cleanup files older than N hours (0 = disabled)"
    )


class HotkeyConfig(BaseSettings):
    """Hotkey configuration."""

    key: str = Field(default="f9", description="Hotkey for start/stop recording")
    pid_file: str = Field(
        default="/tmp/f9-asr-recording.pid", description="PID file path"
    )


class UIConfig(BaseSettings):
    """UI configuration."""

    show_notifications: bool = Field(
        default=True, description="Show desktop notifications"
    )
    copy_to_clipboard: bool = Field(
        default=True, description="Copy result to clipboard"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
        description="Log format",
    )


class Config(BaseSettings):
    """Main configuration."""

    model_config = SettingsConfigDict(env_prefix="F9_ASR_", case_sensitive=False)

    asr: ASRConfig = Field(default_factory=ASRConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        # Convert nested dicts to config objects
        config_dict = {}
        for section, section_config in yaml_data.items():
            if section == "asr":
                config_dict["asr"] = ASRConfig(**section_config)
            elif section == "audio":
                config_dict["audio"] = AudioConfig(**section_config)
            elif section == "hotkey":
                config_dict["hotkey"] = HotkeyConfig(**section_config)
            elif section == "ui":
                config_dict["ui"] = UIConfig(**section_config)
            elif section == "logging":
                config_dict["logging"] = LoggingConfig(**section_config)

        return cls(**config_dict)

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        level = getattr(logging, self.logging.level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format=self.logging.format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
