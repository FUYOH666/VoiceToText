# Changelog

## [1.2.2] - 2026-04-02

### Added
- **Whisper tail artifact filter**: strips common RU/EN trailing hallucinations (subtitles, “thanks for watching”, etc.) after transcription and before paste; configurable under `text_processing` (`strip_whisper_tail_artifacts`, `whisper_artifact_languages`). See `docs/WHISPER_ARTIFACTS.md`.

## [1.2.1] - 2026-03-23

### Fixed
- **Зависание при остановке записи:** `stream.stop()` в sounddevice ждёт буферы PortAudio и мог блокировать горячую клавишу навсегда (после сна, Bluetooth). Используется `abort()` + `close()`.

## [1.2.0] - 2026-03-12

### Added
- **Remote ASR engine** (`remote_asr`): transcribe via Tailscale on a Linux GPU server — frees Mac resources
- **Lazy engine imports**: only the selected engine is loaded; with `remote_asr`, MLX is never imported (~3 GB RAM saved)
- **`.env.vtt2`** (gitignored): service env vars (e.g. `LOCAL_AI_ASR_BASE_URL`) — `--install` injects them into the launchd plist

### Changed
- **Memory with remote_asr**: ~120 MB on Mac vs ~3.5 GB with local MLX (model runs on server)
- **Default config**: can be set to `remote_asr` in `config.yaml` for lightweight operation
- **README**: updated with `.env.vtt2` setup, mode comparison, memory optimization docs

## [1.1.0] - 2026-03-02

### Added
- **launchd service**: `--install` / `--uninstall` / `--status` for auto-start on login and restart on crash
- **PID file**: single-instance protection prevents duplicate processes
- **Log rotation**: RotatingFileHandler (10 MB x 5 files) at ~/Library/Logs/vtt2/
- **Signal handling**: graceful shutdown on SIGTERM (used by `launchctl stop`)
- **`--verbose` flag**: enable DEBUG logging from CLI

### Fixed
- **Critical: chunk text merge** was removing duplicate words, corrupting transcription output
- **Thread safety**: `is_recording` / `is_processing` flags now protected by `threading.Lock`
- **ENV overrides** (`VTT2_` prefix) were parsed but never applied to config
- **`/tmp` cleanup** was deleting files from system `/tmp` directory; now only cleans app cache
- **Bare `except:`** in health_check replaced with `except Exception:`
- **Duplicate `psutil`** dependency (>=5.9.0 and >=7.0.0) consolidated to >=7.0.0
- **Duplicate initialization** of `_model_cache` / `_transcription_count` in MLXWhisperTranscriber

### Changed
- **Project structure**: `src/src/` renamed to `src/vtt2/`, `tests/tests/` flattened to `tests/`
- **Log file default**: logs now written to `~/Library/Logs/vtt2/vtt2.log` (was console-only)
- **README**: rewritten with correct paths, service setup, and architecture docs
- Deleted legacy `requirements.txt` (uv uses `pyproject.toml` + `uv.lock`)
- `uv.lock` now committed to repository (was in .gitignore)

## [1.0.1] - 2025-11-24

### Fixed
- 🔧 **Fixed pynput GlobalHotKeys compatibility**: Updated hotkey handler to accept `injected` argument required by pynput 1.8.0+
- 🔧 **Improved error handling**: Added better exception handling for pynput compatibility issues
- 🔧 **Fallback mechanism**: Enhanced fallback to regular Listener when GlobalHotKeys fails

## [1.0.0] - 2025-11-23

### Added
- 🚀 **M4 Max optimization**: Optimized for MacBook Pro M4 Max with 128GB RAM
- 🌍 **Auto language detection**: Automatically detects language (Russian, Chinese, English, Japanese, etc.)
- 📦 **Long recordings support**: Optimized for 15-45 minute recordings with chunked processing
- ⚙️ **Batch processing**: Utilizes all 40 GPU cores on M4 Max (batch_size=6)
- 🔄 **24/7 operation**: Automatic memory management and error recovery
- 💾 **Memory Manager**: Automatic memory cleanup and monitoring
- 🧹 **Periodic cleanup**: Automatic memory cleanup every 10 transcriptions
- 📊 **Speed testing**: Added `test_transcription_speed.py` for performance testing
- 🎯 **Large-v3 model**: Default model changed to `whisper-large-v3-mlx` for maximum quality

### Performance
- **Speed**: ~42x real-time (tested on M4 Max)
  - 5-minute recording: ~6 seconds
  - 15-minute recording: ~20 seconds
  - 45-minute recording: ~1 minute
- **Memory**: Optimized memory usage with automatic cleanup
- **Stability**: Error recovery and automatic component reinitialization

### Changed
- Default model: `mlx-community/whisper-medium` → `mlx-community/whisper-large-v3-mlx`
- Default language: `"ru"` → `"auto"` (automatic detection)
- Memory limit: Increased to 16GB for M4 Max
- Chunk size: 30 seconds with 2 seconds overlap
- Batch size: 6 for optimal GPU utilization

### Configuration
- Added `performance.auto_cleanup_enabled` (default: true)
- Added `performance.cleanup_threshold_percent` (default: 75)
- Added `performance.periodic_cleanup_interval` (default: 10)
- Added `transcription.mlx_whisper.language` (default: "auto")
- Added `transcription.mlx_whisper.chunk_size_seconds` (default: 30)
- Added `transcription.mlx_whisper.chunk_overlap_seconds` (default: 2)
- Added `transcription.mlx_whisper.batch_size` (default: 6)

### Fixed
- Fixed auto-paste functionality (save active app before recording)
- Fixed health check command (exclude "engine" from status check)
- Improved error handling and recovery
- Reduced warning noise (changed some warnings to debug level)

### Documentation
- Updated README with M4 Max optimizations
- Added 24/7 operation guide
- Added speed testing instructions
- Added memory management documentation
- Updated configuration examples

