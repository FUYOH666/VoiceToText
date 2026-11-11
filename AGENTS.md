# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, Cursor, Copilot, …) working in this repository. Humans: see [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

VoiceToText: local voice typing for Apple Silicon Macs. Two processes:

- `macos/VoiceToText/` — Swift menu bar app (hotkey, recording, paste). Built with plain `swiftc` by `macos/scripts/build.sh`; there is no Xcode project and no SwiftPM manifest.
- `src/vtt2/` — Python FastAPI server on `127.0.0.1:8765` (OpenAI audio API + model management). Runs one MLX model at a time.

Both start at login as LaunchAgents (`service/*.plist`, installed by `uv run python src/vtt2/main.py --install`).

## Layout

| Path | What |
|---|---|
| `src/vtt2/stt_server.py` | HTTP API: `/v1/audio/transcriptions`, `/v1/audio/translations`, health |
| `src/vtt2/server/` | Inference worker (one slot, priorities), error contract, body limits, `/v1/models` API |
| `src/vtt2/transcription/` | Engines: `mlx_engine.py` (Whisper), `qwen_engine.py` (Qwen3-ASR), `hf_cache.py` |
| `src/vtt2/model_catalog/` | `catalog.yaml` (verified models, memory tiers), registry, downloads |
| `src/vtt2/audio/`, `src/vtt2/text/` | Decoding, silence trim, Whisper artifact filter, loop collapse |
| `src/vtt2/config/loader.py` | Config: repo `config.yaml` < user overlay (`~/Library/Application Support/VoiceToText/config.yaml`) < `VTT2_*` env |
| `macos/VoiceToText/Sources/VoiceToTextCore/` | Testable Swift core: HTTP clients, dictation store, glossary, clipboard |
| `macos/VoiceToText/Sources/VoiceToText/` | App: state machine, hotkeys, recorder, paster, menu |
| `scripts/` | `install.sh`, `uninstall.sh`, `prefetch_model.py`, `sync_version.py` |
| `docs/STT_API.md` | The API contract (status codes and `error.code` values) |

## Commands

```bash
uv sync --frozen --extra dev --extra qwen    # Python env (Python 3.12, see .python-version)
uv run pytest -q                              # server tests; never download real models
bash macos/scripts/test.sh                    # Swift core tests (hand-rolled runner, no XCTest)
bash macos/scripts/build.sh                   # builds macos/dist/VoiceToText.app, minos 13.0
uv run python scripts/sync_version.py --check # one version everywhere; pyproject.toml is the source
uv lock --check
```

CI (`.github/workflows/ci.yml`, macOS arm64) runs all of the above plus a secret and personal-path scan.

## Rules

- Keep the server loopback-only. Never bind other hosts.
- Tests must not download models or reach the network; mock `huggingface_hub` and engines (see `tests/test_model_catalog.py`, `tests/test_qwen_engine.py`). Tests get a temp `VTT2_USER_DIR` automatically (`tests/conftest.py`).
- User choices go to the user overlay via `model_catalog.registry.write_selection`, never into the tracked `config.yaml`.
- New server errors use `server.errors.APIError` with a code documented in `docs/STT_API.md`. Clients retry only `429 busy` and `503 model_loading`.
- New Swift core files must be added to the explicit file list in `macos/scripts/build.sh` (tests compile `Sources/VoiceToTextCore/*.swift` automatically).
- New catalog entries: verify the repo, size and commit with `huggingface_hub.HfApi().model_info(repo, files_metadata=True)` and pin `verified_revision`. Qwen3-ASR must be a `moona3k/*` mlx-qwen3-asr checkpoint.
- Do not stop or restart the user's running service (`launchctl` labels `ai.vtt2`, `ai.vtt2.stt`). For live checks run a second server: `VTT2_STT_SERVER_PORT=8766 VTT2_USER_DIR=/tmp/vtt-test .venv/bin/python src/vtt2/main.py --serve-stt`.
- No absolute personal paths or secrets in tracked files (CI greps for them).
- Bump versions only through `scripts/sync_version.py` and `uv lock`.
