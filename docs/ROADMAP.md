# VoiceToText: engineering review and roadmap

VoiceToText is local dictation for Apple Silicon: press Option+Space, speak, and the text is pasted into the active window. It is built for people who dictate all day, including mixed Russian and English with technical terms, and for agents that call a local speech-to-text API.

This document records an engineering review of the `mlx-v1.1` line at commit `42a05f8` and the plan for turning it into a product that ordinary Mac users can install and trust. File and line references point at that commit; the fixes are tracked in the stages below.

## Status (v2.2.0, 2026-11-11)

| Stage | Status | Where |
|---|---|---|
| 0. Repository hygiene | Done: `mlx-v1.1` became `main`, old lines archived as tags, CI, single version source, macOS 13 build | #1, #3 |
| 1. Reliability | Done: server fixes (1a), inference worker and error contract (1b), client never loses a dictation (1c), Whisper anti-loop | #2, #4, #5, #6 |
| 2. Model registry and choice | Done: catalog of quantized models with memory tiers, picker API, «Модель ▸» menu, custom Hugging Face repos | #7, #8 |
| 3. Dictation UX | Partly: push-to-talk, glossary of terms, history, Esc, sounds, status icons, English translation. Open: settings window, recording HUD with level meter, permission onboarding, removing the legacy rumps UI | #9, #11, v2.2.0 |
| 4. Distribution without a Developer ID | Partly: one-command installer that builds locally (4a). Open: prebuilt signed releases from CI, DMG, in-app updates | #10 |
| 5. Later | Open: streaming, Silero VAD, diarization, optional «готовое сообщение» via the user's own local LLM | — |

Scorecard after v2.2.0 (was 20/40): quality 4.5, reliability 4, dictation UX 3.5, model choice 4, installation 3.5, code and tests 4, repository 4, privacy 4.5 — about 32/40.

## How it works today

- **Swift menu bar app** (`macos/VoiceToText`): global hotkey, 16 kHz recording, WAV encoding, HTTP request, paste through the clipboard and Cmd+V.
- **Python STT server** (`src/vtt2/stt_server.py`) on `127.0.0.1:8765`: OpenAI-compatible `POST /v1/audio/transcriptions`. Engines: Qwen3-ASR 1.7B 8-bit (default), MLX Whisper, whisper.cpp, remote.
- **Startup:** LaunchAgents in `service/*.plist` start both processes. The plists are bound to the repository folder.

## Product decisions

- **Audience, in stages.** First the core: reliability, quality and model choice. Then an app that ordinary Mac users can run without a terminal.
- **One product line.** `mlx-v1.1` becomes `main`. The older `main` (monorepo with Linux) and `product-unified` lines move to archive tags. CI, the version sync script and the issue templates are carried over from `product-unified`. Linux is no longer supported.
- **Models.** A curated, tested list plus a field for any Hugging Face repo id.
- **No Apple Developer ID.** Releases are distributed without notarization (see Stage 4).

## Scorecard

| Area | Score | Summary |
|---|---|---|
| Recognition quality | 4/5 | Qwen3-ASR 1.7B 8-bit runs ~30× faster than real time (110 s of audio in 3.1 s). But the "artifact" filter removes real words, and the term glossary is never used. |
| Reliability | 2/5 | Any error loses the dictation. The hotkey can hang for up to 13 minutes. Server logs show repeated `LibsndfileError` responses with status 500. |
| Dictation UX | 2/5 | Toggle only. The icon does not show recording. No sounds. The clipboard is not restored. No settings, no history. |
| Model choice | 2/5 | Two engines are hard-coded. Switching rewrites the tracked `config.yaml`. A new engine needs edits in seven places. |
| Installation | 1/5 | About 12 terminal steps, with paths hard-coded in plists. The binary is built with `minos` 27.x and will not launch on macOS 13–26. Releases have no assets. |
| Code and tests | 3/5 | Tidy code and about 100 mock-based tests. But no CI, 782 lines of legacy rumps UI are imported into the server, env-var mapping is broken, and three near-identical configs exist. |
| Repository | 2/5 | Three unrelated history lines. The README on `main` describes a different product. Version tags are out of order: v2.1.1 is older than v1.7.0. |
| Privacy | 4/5 | Loopback only, and transcripts are not logged. But every model load contacts huggingface.co, and text can be pasted into a password field. |

## Confirmed critical bugs

1. **The filter removes real words.** `src/vtt2/text/whisper_artifacts.py:191-203` strips listed phrases from the end of every segment, for every engine. Verified: "К дому приехала полиция" → "К дому приехала", "Это вызвало смех" → "Это вызвало", "Он сказал: Thank you." → "Он сказал:".
2. **The app does not launch on older macOS.** `macos/scripts/build.sh:14` calls `swiftc` without `-target`, so the binary gets the build machine's SDK version as `minos` (27.x), although `Info.plist` declares 13.0.
3. **Any error loses the dictation.** `AppState.swift:172-199` discards the WAV on timeout, 413 or a server crash.
4. **The hotkey hangs.** The client retries every 503 for up to 780 s (`STTClient.swift:61,75`), and the server also returns 503 for a permanent model load failure. There is no cancel.
5. **Race after a timeout.** `stt_server.py:434-486`: when `wait_for` times out, the lock is released while the inference thread is still running. Two transcriptions can hit the same model, and the idle unloader can free a model that is in use.
6. **Decode errors return 500.** `audio/decode.py:122-133` lets `LibsndfileError` escape. Decoding blocks the event loop, and the LaunchAgent plist has no `PATH` to ffmpeg.
7. **Paste always reports success.** `Paster.swift:137` returns `true` even when paste failed without Accessibility. The clipboard is not restored. Text is also pasted into secure input fields.

Also found:

- Env-var mapping is broken: `config/loader.py:322` splits the name on every `_`.
- MLX Whisper has no `release()`, so idle unload frees nothing.
- The Qwen forced aligner is recreated on every request.
- `setup-local-signing.sh:44` fails with the system LibreSSL (`-legacy` is not supported).
- Versions disagree: app 1.5.1, Python package 1.7.0, `__version__` 1.0.0. Fixed by the CI and versions PR.

## What is already good

- A fast and accurate default model, and an OpenAI-compatible API for agents (`verbose_json`, timestamps, per-request language and prompt).
- Small, readable files and testable seams in Swift (`MockURLProtocol`, injected dependencies).
- Idle model unload, and a stable local signing identity that keeps TCC grants across rebuilds.

## Architecture decisions

- **The Python server stays the inference engine through Stage 4.** Agents depend on the HTTP API, the model ecosystem (mlx-audio, mlx-qwen3-asr, huggingface_hub) lives in Python, and MLX in Python and Swift runs the same Metal kernels. A Swift-native "Lite" engine (WhisperKit / FluidAudio) is a Stage 5 option if the eval justifies it.
- **Models.** Standardize on `mlx-audio` (one API for Whisper, Parakeet, Voxtral, Canary, Nemotron). Keep `mlx-qwen3-asr` for Qwen until mlx-audio matches it on quality and speed.
- **User config** moves to `~/Library/Application Support/VoiceToText/config.yaml`, layered over built-in defaults. The tracked `config.yaml` becomes an example. Swift and Python read the same path.
- **Distribution without a Developer ID:**
  - Main path: a `curl | sh` installer. It downloads a prebuilt zip signed with a stable self-signed certificate, verifies SHA-256 and installs into `~/Applications`. curl does not set the quarantine attribute, so Gatekeeper does not block the app.
  - For everyone else: a DMG with an illustrated "Open Anyway" guide for System Settings. macOS 15+ removed the Control-click bypass. Behaviour on macOS 26 still needs checking.
  - One certificate for all releases keeps the Microphone and Accessibility grants across updates.
- **Versioning.** The next release is **v2.2.0**, so it sorts after the existing v2.x tags of the old line. `pyproject.toml` is the single source of the version; `scripts/sync_version.py` writes it to `Info.plist`, the config files and `__init__.py`, and CI checks it.

## Roadmap

### Stage 0. Repository hygiene

1. **Branches.** Tag `archive/main-2026-11` (`192e98c`) and `archive/product-unified-2026-11` (`4fbf9ed`). Delete `main` and `product-unified`, then rename `mlx-v1.1` → `main` (GitHub keeps the default branch and redirects).
2. **Swift build PR** (`macos/` only):
   - `build.sh` and `test.sh` pass `-target arm64-apple-macos13.0`.
   - `setup-local-signing.sh` uses `-keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1` instead of `-legacy`.
   - Drop the unneeded Input Monitoring request and the unused Apple Events entitlement.
   - Merge the two Swift test suites into one that actually runs.
3. **CI and versions PR** (`.github/`, `scripts/`, `docs/`):
   - `.github/workflows/ci.yml`, macOS arm64 only: `uv sync --frozen`, pytest, `test.sh`, `build.sh`, a `minos` check.
   - `scripts/sync_version.py` with `pyproject.toml` as the single version source.
   - Issue templates.
   - This document.

### Stage 1. Reliability

**1a. Safe server fixes** (`src/`, `tests/`, `service/`):

- The artifact filter runs only for the Whisper family, only on whole segments and only on exact matches. Ordinary words ("ПОЛИЦИЯ", "СМЕХ", "ПЕСНЯ", "ВЗРЫВ", "Thank you.", "Поехали!") leave the list.
- Any decode error → 400 `invalid_audio`. Decoding runs in `asyncio.to_thread`, and `service/ai.vtt2.stt.plist` gets a `PATH` that includes `/opt/homebrew/bin`.
- Env-var mapping uses `__` as the nesting separator (`VTT2_STT_SERVER__PORT`).
- `release()` for MLX Whisper; cache the Qwen aligner.
- If the model is already cached, load it locally (`local_files_only` / `HF_HUB_OFFLINE`) without a network request.
- Tests: "…полиция" survives the filter, a corrupt file returns 400 (not 500), nested env vars work.

**1b. Inference worker** (`stt_server.py` and a new `src/vtt2/server/`):

- A single-threaded executor: the lock is released only when inference has actually finished. Idle unload checks `active_jobs == 0`.
- An OpenAI-style error contract `{"error": {...}}`, documented in `docs/STT_API.md`:

  | Response | Client retries? |
  |---|---|
  | 400 `invalid_audio` | no |
  | 413 (file too large or too long) | no |
  | 429 `busy` + `Retry-After` | yes |
  | 503 `model_loading` | yes |
  | 500 `model_load_failed` | no |
  | 504 `transcription_timeout` | no |

- Upload size limit in ASGI middleware, plus `max_audio_seconds`.
- The server moves to `src/vtt2/serve.py` without importing rumps. The legacy UI moves to a `legacy-ui` extra.

**1c. Client reliability** (in parallel with 1b, `macos/VoiceToText/Sources` only):

- The WAV is saved before upload to `~/Library/Application Support/VoiceToText/recordings/`, with history in `history.jsonl` and a "Retry last" menu item.
- Retry only on 429/503, capped at 180 s. Esc or the hotkey cancels processing.
- The clipboard is saved and restored. No paste while secure input is on. Paste returns its real result.
- State icons (idle / recording / processing / error), sounds, a maximum recording length.

### Stage 2. Model registry and choice

- **`Engine` protocol** (`load / release / transcribe / capabilities`) in `src/vtt2/engines/`, a lazy backend table, and per-backend language code mapping (`ru` / `Russian` / `ru-RU` / auto only). It replaces the if-chains in `transcription/engine.py`, `loader.py` and `stt_server.py`.
- **Catalog** `src/vtt2/models/catalog.yaml`: repo, pinned revision, backend, size, languages, Russian score, post-processing. Plus a user `models.yaml`.
- **Models API:**
  - `GET /v1/models`: list.
  - `POST /v1/models/{id}/download`: download with progress via `snapshot_download` + `tqdm_class`.
  - `DELETE /v1/models/{id}`: delete via `scan_cache_dir`.
  - `POST /v1/models/{id}/activate`: select the model.
  - `POST /v1/models/inspect {repo}`: validate a custom Hugging Face id.
  - `model=` on a transcription request: an installed model is used for that request; a model that is not installed returns 409. A transcription request never starts a download.
- **Swift.** A "Model ▸" menu with sizes, download progress and "Custom Hugging Face model…". It replaces `EngineSwitch.swift`, which rewrites YAML.
- **Candidate list** (the eval decides the final set):

  | Model | Role |
  |---|---|
  | Qwen3-ASR 1.7B 8-bit | Default: RU+EN, punctuation |
  | Qwen3-ASR 0.6B 8-bit | Lightweight |
  | Whisper large-v3-turbo | Multilingual |
  | Whisper large-v3 | Best quality, slow |
  | Parakeet TDT 0.6B v3 | Fastest; Russian quality unclear |
  | GigaAM v3 e2e_rnnt | Experimental: Russian specialist, ~225 MB, via ONNX or an MLX port |

  No 4-bit variants for Russian: WER rises noticeably.
- **Eval.** `eval/manifest.jsonl` (audio stays out of git) and `scripts/eval_asr.py` measure WER/CER (jiwer, ё→е), RTF and peak memory on 50–100 real RU+EN phrases. The term glossary passed as `prompt` is checked separately.

### Stage 3. Dictation UX

- **Settings window** (SwiftUI):
  - General: hotkey, toggle or push-to-talk, sounds, maximum length, clipboard restore.
  - Models.
  - Language and term glossary (sent as `prompt`).
  - History.
  - Server: status, logs, restart.
- Onboarding with live permission status.
- A HUD with input level and a timer; user-defined text replacements.
- Remove the legacy rumps UI: the UI in `main.py`, `system/*`, `audio/recorder.py`, `utils/pid_manager.py`, `utils/memory_manager.py`.
- Done when a user never has to edit YAML.

### Stage 4. Distribution without a Developer ID

- **The app bundle** contains the server sources, `uv.lock`, a pinned `uv` binary and a launcher.
- **First-run assistant:** permissions → `uv sync --frozen` into Application Support → choose and download a model → register the server with `SMAppService.agent`.
- **Releases from GitHub Actions** on `v*` tags: the self-signed certificate lives in repository secrets; outputs are a zip, a dmg and `SHA256SUMS`.
- **Delivery:** the `curl | sh` installer and the DMG with a guide. The app checks GitHub Releases for updates and verifies SHA-256 and the signature.
- **To verify:** running the bundled `uv` from a quarantined app, `SMAppService` with a self-signed bundle, and TCC grants surviving updates on macOS 15 and 26.

### Stage 5. Later

Streaming (Voxtral Mini Realtime, partial text in the HUD), VAD (Silero), diarization for long recordings, optional LLM clean-up of the text, and a Swift-native "Lite" engine.

## Sequencing

- Stage 0 and Stage 1a are three PRs with no shared files: `macos/`; `.github/` + `scripts/` + `docs/`; `src/` + `tests/` + `service/`.
- 1b and 1c then run in parallel: server and client share only the contract in `docs/STT_API.md`. The eval harness (`eval/`) can be built alongside them.
- Stage 2 starts after Stage 1 is merged, because it touches the same `loader.py`, `stt_server.py`, `AppConfig.swift` and `EngineSwitch.swift`.

## Verification

- **Python:** `uv sync --frozen --extra dev --extra qwen`, then `uv run pytest -q`. New tests pass and old ones still pass.
- **Swift:**
  - `macos/scripts/test.sh` and `macos/scripts/build.sh`.
  - `vtool -show-build` (or `otool -l`) on the built binary shows `minos 13.0`.
  - `setup-local-signing.sh` succeeds with `/usr/bin/openssl` (LibreSSL).
- **Live server check** on a spare port (`VTT2_STT_SERVER__PORT=8766`), leaving the running service on 8765 alone:
  - `say -v Milena "К дому приехала полиция"` → 16 kHz WAV → POST: the word «полиция» is still in the response.
  - A corrupt file returns 400.
  - Two model reloads succeed offline (`HF_HUB_OFFLINE=1`).
- **CI** is green on every PR.
- **After merge:** restart the server LaunchAgent (`launchctl kickstart -k gui/$(id -u)/ai.vtt2.stt`) and dictate in the real app.
