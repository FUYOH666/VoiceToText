# Changelog

## [Unreleased]

## [2.1.1] - 2026-05-28

### Fixed
- **F9 config:** `LOCAL_AI_ASR_BASE_URL` in `.env.local` no longer overrides `linux-f9-local` (only `linux-f9-edge`)

### Changed
- **Default profile:** `mac-m1-local` (local MLX on M1) in `config.yaml`
- Startup log shows active profile, engine, and MLX model name
- Clearer errors when `.env.local` is missing for remote ASR

### Added
- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), GitHub issue/PR templates
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md), [README.ru.md](README.ru.md)
- README badges and «free & private» positioning

## [2.1.0] - 2026-05-28 — Golden Standard

### Added
- **`vtt` CLI**: `doctor`, `mac run`, `linux run`, `profiles list`, `validate-config`
- **Whisper tail artifacts**: `strip_trailing_whisper_artifacts` + `docs/WHISPER_ARTIFACTS.md`
- **F9 on profiles**: `F9Config.from_profile()`, `--profile` / `F9_PROFILE`
- **`config/f9_base.yaml`**, `scripts/sync_version.py` (semver = pyproject = base.yaml)
- **CI**: `.github/workflows/ci.yml` (pytest, IP grep, profile matrix, mock ASR)
- **Fresh install**: `.github/workflows/fresh-install.yml` (macOS `uv sync --extra mac`)
- **Docs**: `GOLDEN_STANDARD.md`, `asr-api.md`, `docs/enterprise/INSTALL.md`
- **Optional `mac` extra**: GUI/audio deps for CI-friendly core install on Linux

### Changed
- Linux scripts: no hardcoded `/home/ai/...`; deprecated toggles point to `vtt linux run`
- README / cutover checklist aligned with golden standard flow

### Fixed
- Regression: whisper artifact stripping missing on `product-unified`

## [2.0.0] - 2026-05-28

### Added
- **Branch `product-unified`**: profile-based config (`config/base.yaml` + `config/profiles/*`)
- **Mac profiles**: `mac-m1-local`, `mac-m1-remote`, `mac-m4-local`, `mac-m4-remote`
- **Linux F9** under `clients/linux/` (from legacy `main`)
- **Shared** `vtt_asr_client` package for Mac remote ASR and Linux F9
- **CLI** `--profile` / `VTT2_PROFILE`; health check shows active profile
- Docs: `PRODUCT_MATRIX.md`, `ENTERPRISE_EDGE.md`, `CUTOVER_CHECKLIST.md`, `LEGACY_BRANCHES.md`
- **Optional deps** `local-mlx` for edge-only installs without MLX wheels

### Changed
- **Secrets**: ASR URL only via `.env.local` / `LOCAL_AI_ASR_BASE_URL` (no Tailscale IP in git)
- **Default profile**: `mac-m1-remote` in `config.yaml`
- Project version **2.0.0** (`voicetotext` in `pyproject.toml`)

### Fixed

## [1.1.x] — mlx-v1.1 legacy

### Fixed
- **Иконка меню**: после остановки записи красная точка сменяется на «обработка» (`menu_bar.icon_processing`), а не висит как «идёт запись» до конца транскрипции

### Changed
- **Локальная MLX-модель по умолчанию**: `mlx-community/whisper-large-v3-turbo-q4` (Large v3 Turbo, Q4)
- **Автозапуск**: launchd не даёт доступ к микрофону — рекомендуется Login Items (`start-vtt2.app`)
- **Remote ASR**: по умолчанию используется удалённый ASR через TailScale вместо локального MLX Whisper

### Added
- **`scripts/prefetch_mlx_model.py`**: скачивает веса `mlx_whisper.model_name` из `config.yaml` в HF cache без запуска GUI VTT2
- **start-vtt2.app**: AppleScript-приложение для Login Items (автозапуск с доступом к микрофону)
- **Проверка тишины**: уведомление при записи без звука (нет доступа к микрофону)
- **Уведомления**: при пустом результате, неудачной вставке, отсутствии микрофона

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

