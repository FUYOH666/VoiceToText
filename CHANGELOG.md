# Changelog

## [1.6.0] - 2026-08-16

### Added
- OpenAI-compatible `response_format` on `POST /v1/audio/transcriptions`: `json` (default `{text}`), `verbose_json` (full transcript + segment timecodes), `text`.
- Optional `timestamp_granularities` / `timestamp_granularities[]=word` for word-level timings in `verbose_json`.
- HTTP path uses native MLX Whisper decode (`transcribe_detailed`) so ~10 minute agent jobs keep correct offsets (custom long-audio chunk merge is not used here).

### Changed
- Default `stt_server.max_upload_mb` is 40 (headroom for ~10 min 16 kHz WAV). Timeout stays 600s. Concurrency remains 1 — a long job still blocks Option+Space until it finishes.

## [1.5.1] - 2026-08-15

### Changed
- Menu bar mark is a waveform (not a second system microphone). Recording state stays in the menu; macOS already shows the orange privacy pill.
- Paste uses the same Cmd down/up + annotated/session tap path as the working Python injector.
- Accessibility / Input Monitoring: log only on dictate; system prompt only from the menu item «Разрешения…» (ad-hoc rebuilds otherwise fight a stale TCC row).

## [1.5.0] - 2026-08-15

### Added
- Native Swift menubar app (`macos/VoiceToText`): Option+Space, local STT client, paste — no Python in Dock.
- `--install` prefers `VoiceToText.app` as login item; rumps LaunchAgent remains the fallback.
- `macos/scripts/build.sh` (local ad-hoc `.app`) and `macos/scripts/release.sh` (Developer ID + notarytool + staple). Signing secrets stay in gitignored `macos/Signing.xcconfig`.

### Changed
- Canonical contact email: `private@scanovich.ai`.

## [1.4.0] - 2026-08-15

### Added
- **Idle unload** for STT: `stt_server.preload_on_start` + `stt_server.idle_unload_seconds` — weights load on demand and drop after idle (frees GPU/unified footprint).
- **Config profiles:** [`config.resident.yaml`](config.resident.yaml) (always-on snapshot) and default [`config.yaml`](config.yaml) (idle unload, 15 min).
- Client `local_stt.warmup_wait_seconds` — retry on 503 while model loads.
- `/healthz` fields: `loading`, `idle_unload_seconds`, `preload_on_start`.

### Changed
- Default profile no longer preloads large-v3 at login; first dictate after idle may cold-start.
- `batch_size` default in idle profile: 4 (was 6).
- Default `mlx_whisper.language` is `ru` (both profiles) — `auto` on long Russian takes could return `nn` / near-empty text.
- `--health` checks `local_stt` via `GET /healthz`.
- Menubar uses accessory activation policy (less Python Dock flash).

### Fixed
- Hotkey / startup no longer call `rumps.alert` (NSAlert from LaunchAgent appeared behind apps). Errors go to log + menu-bar status; alerts stay on explicit menu clicks.
- `--install` kills leftover menubar processes (not `--serve-stt`), clears `vtt2.pid`, then reloads UI so `local_stt` client updates after STT reload.

## [1.3.0] - 2026-07-25

### Added
- **Local STT HTTP API** (`ai.vtt2.stt`): OpenAI-compatible `POST /v1/audio/transcriptions` on `127.0.0.1:8765`, plus `GET /healthz` and `GET /readyz` (503 until model warmup).
- **Menubar thin client** (`transcription.engine: local_stt`): Option+Space records locally, transcribes via loopback — one resident `mlx_whisper` shared with agents.
- LaunchAgent template [`service/ai.vtt2.stt.plist`](service/ai.vtt2.stt.plist); `--install` / `--uninstall` / `--status` manage STT + menubar.
- CLI: `uv run python src/vtt2/main.py --serve-stt`
- Agent note: [`docs/STT_API.md`](docs/STT_API.md)
- Audio decode helper for uploads (soundfile + ffmpeg for ogg/webm/m4a)
- Deps: `fastapi`, `uvicorn`, `httpx`, `python-multipart`

### Changed
- Default `config.yaml`: menubar `local_stt`, model owned by `stt_server.engine: mlx_whisper`
- Whisper tail-artifact stripping applied on the STT server for all HTTP clients

## [1.2.9] - 2026-04-20

### Added
- **Whisper tail list (EN):** `Transcription by CastingWords`, `Thank you for listening`, `That's all`, `Thanks!` (по обсуждениям Whisper / WhisperLive)

### Changed
- **Docs:** `WHISPER_ARTIFACTS.md` — дополнительные ссылки на discussion и HF-датасет; пояснение про короткие EN-слова.

## [1.2.8] - 2026-04-17

### Changed
- **Docs:** README troubleshooting notes v1.2.6 queue-drain fix; `docs/WHISPER_ARTIFACTS.md` — явная отсылка к `whisper_artifacts.py` как к полному списку фраз.

## [1.2.7] - 2026-04-08

### Added
- **Whisper tail list (RU):** `Субтитры сделал DimaTorzok`

## [1.2.6] - 2026-04-08

### Fixed
- **Зависание после «Останавливаем запись»:** слив очереди чанков после `InputStream` переведён на `get_nowait()` вместо `empty()` + `get()` — иначе возможна гонка с аудиоколбэком и вечная блокировка на `Queue.get()`.

## [1.2.5] - 2026-04-04

### Added
- **Whisper tail list (RU):** `Субтитры создавал DimaTorzok`

## [1.2.4] - 2026-04-02

### Added
- **Whisper tail list (RU):** `Спасибо за субтитры Алексею Дубровскому!`

## [1.2.3] - 2026-04-02

### Changed
- **README:** configuration example matches real `config.yaml` nesting; clarify default engine (`remote_asr` in bundled config) vs local MLX; separate “offline after download” (local) from remote ASR (needs server).

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

