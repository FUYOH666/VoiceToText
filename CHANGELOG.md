# Changelog

## [2.2.0] - 2026-11-11

The first release after a full engineering review ([docs/ROADMAP.md](docs/ROADMAP.md)). The version jumps from 1.7.0 so the tag sorts after `v2.1.1` from the archived old line.

### Highlights
- **Install in one command:** `curl -fsSL https://raw.githubusercontent.com/FUYOH666/VoiceToText/main/scripts/install.sh | bash`. Everything is built on your Mac, so no Developer ID or notarization is needed.
- **Choose a model in the menu.** Verified MLX checkpoints are listed, quantized first, with a recommendation for your Mac's memory. Models download in the background, and you can add your own from Hugging Face.
- **Speak any language, get English.** «Перевод на английский» uses Whisper's built-in translation (`POST /v1/audio/translations`).
- **Push-to-talk:** hold Option+Space, speak, let go. A tap still toggles.
- **Nothing is lost:** every recording is saved before it is sent, and the menu has History and Retry. Esc cancels.
- **Whisper without loops:** the decoder can recover from repetition, silence is trimmed, and repeats are collapsed. Real words are no longer cut by the artifact filter.

### Added
- `POST /v1/audio/translations` (OpenAI-compatible), for Whisper models that translate well (large-v3, large-v3 8-bit, small). Other models return `400 translation_unsupported`. The catalog has a `translates` flag.
- Model catalog (`src/vtt2/model_catalog/catalog.yaml`) and API:
  - `GET /v1/models`;
  - `POST|GET /v1/models/{id}/download`;
  - `POST /v1/models/{id}/activate`;
  - `DELETE /v1/models/{id}`;
  - `POST /v1/models/custom`.

  The choice is stored in `~/Library/Application Support/VoiceToText/config.yaml`, layered over the repo config.
- The menu bar app gained:
  - «Модель ▸» with sizes, ★ for the recommended model and background download with progress;
  - «Перевод на английский»;
  - «Словарь терминов…», which sends your terms as the `prompt`;
  - History and «Повторить последнюю запись»;
  - push-to-talk, Esc to cancel, a sound toggle, and status icons for processing and errors.
- `scripts/install.sh`, `scripts/uninstall.sh` (it only removes services owned by its own copy) and `scripts/prefetch_model.py`.
- An inference worker owns all model access:
  - a slot is freed only when inference has really finished;
  - dictation gets priority over long files;
  - error bodies have the OpenAI shape;
  - 429/503 carry `Retry-After`;
  - there is an early body-size limit and `max_audio_seconds`.
- CI on macOS arm64 (secret/path scan, lock check, version sync, pytest, Swift tests, build, minos check). `scripts/sync_version.py` keeps one version everywhere.

### Changed
- The app builds for macOS 13+ (`minos 13.0`; it said 27.0 before). Input Monitoring is no longer requested; only Microphone and Accessibility are needed.
- Whisper decoding:
  - temperature fallback is on;
  - `condition_on_previous_text=false`;
  - leading and trailing silence is trimmed before decoding, and timecodes are kept on the original timeline;
  - repetition loops are collapsed.
- The clipboard is restored after a paste. Nothing is pasted into password fields (secure input). The dictated text is marked transient so clipboard managers skip it.
- The client retries only `429` and `503 model_loading`, for at most 180 s. `/healthz` gives up after 3 s, and other errors fail at once with a readable status.
- Cached models load from disk without contacting huggingface.co. `release()` on idle unload frees MLX Whisper memory.
- `VTT2_*` environment overrides resolve against the config schema (`VTT2_STT_SERVER_PORT` works; `__` splits levels explicitly).
- The menu bar icon no longer changes while recording; macOS's orange microphone indicator shows that.

### Fixed
- The artifact filter deleted real words at the end of a segment (for example "…приехала полиция" became "…приехала") for every engine. It now runs only for Whisper, and short phrases are removed only when they are a whole line or segment.
- Undecodable uploads returned 500 instead of 400.
- On long recordings with pauses, Whisper silently dropped whole stretches of speech.
- Several races: a timed-out request released the model while inference was still running, and the idle unloader could release the model mid-job.
- `.python-version` is tracked, so a fresh `uv sync` uses Python 3.12. It picked 3.14 before, and llvmlite failed to build.

### Removed
- The Whisper/Qwen menu switch, which rewrote the git-tracked `config.yaml` (replaced by «Модель ▸»).

## [1.7.0] - 2026-10-06

### Added
- `POST /v1/audio/transcriptions` applies `language` and `prompt`. Omitted or blank `language` keeps the config code (`ru`). `auto` is autodetect. A canonical code overrides. Full names and other tokens return `400`. `prompt` is Whisper `initial_prompt` (max 1000 characters).
- Inference log `requested_language` / `effective_language` at the mlx call, so a form-field log is not treated as proof the engine used that language.

### Changed
- Whisper tail phrases are stripped from every segment, then the top-level `text` is rebuilt. Previously only the last segment was cleaned.
- Default upload limit is 80 MB and the request timeout is 1200s. 80 MB covers a typical 20-minute 16 kHz mono WAV, not every 20-minute source file.

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

