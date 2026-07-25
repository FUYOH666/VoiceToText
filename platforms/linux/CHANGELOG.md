# Changelog

All notable changes to this project will be documented in this file.

## [0.1.4] - 2026-07-25

### Fixed

- **notify-send из systemd:** в `f9-asr-launch.sh` задаётся `DBUS_SESSION_BUS_ADDRESS` — снова видны уведомления «Recording started» / предупреждения.
- **Пустая транскрипция:** уточнён выбор микрофона (`device: null` = PipeWire default; встроенный vs Bluetooth) в `config.yaml` и TROUBLESHOOTING (VAD, `wpctl`).

### Changed

- `audio_recorder`: в лог пишется явное ALSA-устройство или default PipeWire.

## [0.1.3] - 2026-04-06

### Fixed

- **systemd + X11:** сервис падал с `Can't connect to display ":0"` при `DISPLAY=:1` (GDM). Добавлен `scripts/f9-asr-launch.sh` — подбор сокета X0/X1/X2 и `XAUTHORITY` для GDM.
- Удалён устаревший `MemoryLimit=` из unit (остаются `MemoryMax` / `MemoryHigh`).

### Changed

- SERVICE.md, TROUBLESHOOTING.md — раздел про DISPLAY и переустановку сервиса.

## [0.1.2] - 2026-02-22

### Added

- **Bluetooth-микрофон** — поддержка гарнитур через WirePlumber (профиль headset-head-unit)
- Документация [docs/BLUETOOTH_MIC.md](docs/BLUETOOTH_MIC.md) — пошаговая настройка
- Параметр `audio.device` в конфиге — явный выбор ALSA-устройства захвата

### Changed

- TROUBLESHOOTING: обновлён раздел про Bluetooth
- README: добавлена ссылка на BLUETOOTH_MIC

## [0.1.1] - 2026-02-09

### Changed

- Updated ASR service integration for Whisper Large v3 Turbo model
- Updated model name in API requests from `qwen3-asr` to `whisper` (for compatibility)
- Updated documentation to reflect new model (Whisper Large v3 Turbo)

## [0.1.0] - 2026-02-09

### Added

- Initial release
- Voice transcription on F9 keypress
- Integration with ASR service on port 8001 (Whisper Large v3 Turbo)
- Audio recording using `arecord`
- OpenAI-compatible API client for ASR service
- Hotkey handler using `pynput`
- Desktop notifications support
- Automatic clipboard copying
- YAML configuration with Pydantic Settings
- Systemd user service for autostart and background operation
- Automatic restart on crashes
- Service installation script (`install-service.sh`)
- Comprehensive documentation (README, INSTALL, SERVICE, QUICKSTART, PRIVACY, TROUBLESHOOTING)
- Structured logging with configurable levels
- Health check for ASR service
- **Automatic cleanup** of temporary audio files (prevents accumulation)
- **Privacy-focused** - no data persistence, only temporary processing
- **Debug file management** - limits debug files to last 5
- **Startup cleanup** - removes old files older than configured age (default: 24 hours)

### Features

- **Audio Recording**: Uses `arecord` for high-quality audio capture
- **ASR Integration**: Connects to existing ASR service instead of local models
- **Hotkey Support**: F9 key to toggle recording
- **Clipboard Integration**: Automatically copies transcription result
- **Notifications**: Desktop notifications for status updates
- **Configuration**: Flexible YAML-based configuration
- **Error Handling**: Comprehensive error handling and logging
- **Automatic Cleanup**: Temporary files are automatically deleted after transcription
- **Privacy**: No data persistence - all processing is temporary
- **Stability**: Automatic restart on crashes via systemd
- **Resource Management**: Automatic cleanup of old files on startup

### Technical Details

- Python 3.12+
- Uses `uv` for dependency management
- Pydantic for configuration validation
- Structured logging with configurable levels
- Graceful shutdown handling
