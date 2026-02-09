# Changelog

All notable changes to this project will be documented in this file.

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
