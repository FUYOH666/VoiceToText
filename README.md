# VTT MLX

**Turn speech into text instantly — wherever you work, no cloud, no subscription.**

---

## The Problem

You type notes, emails, docs for hours. Your voice is 3x faster.

Cloud transcription costs $10–20/month and sends your data elsewhere. Built-in dictation is slow, unreliable, and doesn't paste where you need it.

## The Solution

VTT sits in your Mac menu bar. Press **Option+Space**, speak, text appears where your cursor is.

By default the **Whisper model lives in one local STT process** (`ai.vtt2.stt` on `127.0.0.1:8765`). The menubar is a thin client — same API agents use (OpenClaw, curl, bots). Optional: remote GPU ASR via Tailscale. No subscription. 99 languages, auto-detected. Works in any app.

## Results

- **Before:** 5 min typing a 2-min voice note, or $20/mo for cloud ASR, or two copies of a local model in RAM
- **After:** 2 min voice → instant text. One resident MLX model (~3.5 GB) shared by hotkey + HTTP clients; or remote ASR (~120 MB on Mac)

---

## Quick Start

### Requirements

- Mac with Apple Silicon (M1, M2, M3, M4 — any variant)
- macOS 13+ (Ventura or later)
- 8 GB RAM minimum (see [model selection](#choose-a-model) below)
- [uv](https://docs.astral.sh/uv/) package manager

### Install

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and set up
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
uv sync
```

Default config: menubar uses `local_stt` → `http://127.0.0.1:8765`; the STT service loads `mlx_whisper` (model downloads on first warmup, ~6 GB for large-v3, then offline). Agent API: [docs/STT_API.md](docs/STT_API.md).

### Run

```bash
# Terminal A — STT (owns the model)
uv run python src/vtt2/main.py --serve-stt

# Terminal B — menubar / hotkeys (after readyz is green)
curl -fsS http://127.0.0.1:8765/readyz
uv run python src/vtt2/main.py
```

A microphone icon appears in your menu bar. Press **Option+Space** to record.

### Run as a background service

Installs **two** LaunchAgents: `ai.vtt2.stt` (model + HTTP) and `ai.vtt2` (menubar). Both start on login.

```bash
# Install both
uv run python src/vtt2/main.py --install

# Check status
uv run python src/vtt2/main.py --status

# Remove both
uv run python src/vtt2/main.py --uninstall
```

```bash
# Smoke test STT API
curl -fsS http://127.0.0.1:8765/readyz
curl -fsS -F file=@sample.wav http://127.0.0.1:8765/v1/audio/transcriptions
```

### macOS permissions

On first launch macOS will ask for three permissions. **All three are required:**

| Permission | Why | Where to grant |
|---|---|---|
| Microphone | Record your voice | Privacy & Security > Microphone |
| Accessibility | Global hotkey (Option+Space) | Privacy & Security > Accessibility |
| Input Monitoring | Auto-paste text (Cmd+V) | Privacy & Security > Input Monitoring |

If hotkeys don't work, add your terminal app (Terminal, iTerm, Cursor) to **Accessibility** and **Input Monitoring**, then restart the app.

---

## Deploy This For Your Business

This is open-source. You can run it yourself.

Or I can deploy, customize, and integrate it for your team in **2 weeks** — custom voice workflows, enterprise integrations, deployment on your infrastructure.

**Free consultation** — tell me your use case, I'll tell you if it fits and how fast we can move.

→ **Email:** iamfuyoh@gmail.com  
→ **Telegram:** [@ScanovichAI](https://t.me/ScanovichAI)

---

## Tech Stack

### How it works

1. Press **Option+Space** to start recording
2. Speak (any language — auto-detected)
3. Press **Option+Space** again to stop
4. Menubar POSTs audio to local STT → text is pasted into the active app

Agents use the same `POST /v1/audio/transcriptions` — see [docs/STT_API.md](docs/STT_API.md).

**Local STT (default):** [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) in `ai.vtt2.stt` — one resident model.  
**Remote mode:** set `transcription.engine: remote_asr` — Whisper on your Linux GPU via Tailscale.

### Transcription engines

| Mode | Role | RAM on Mac |
|------|------|------------|
| `local_stt` (default menubar) | HTTP client → `127.0.0.1:8765` | ~120 MB (UI only) |
| STT service `stt_server.engine: mlx_whisper` | Owns the model | ~3.5 GB |
| `mlx_whisper` in menubar | In-process MLX (avoid if STT also running) | ~3.5 GB extra |
| `remote_asr` | Linux GPU via Tailscale | ~120 MB |

**Models (defaults in `config.yaml`):**

| Engine | Model / artifact |
|--------|------------------|
| `mlx_whisper` (STT server) | `mlx-community/whisper-large-v3-mlx` |
| `remote_asr` | `cstr/whisper-large-v3-turbo-int8_float32` |
| `whisper_cpp` | GGML path, e.g. `models/ggml-medium-q5_0.bin` |

Tail-end subtitle-style hallucinations are stripped before paste; see [docs/WHISPER_ARTIFACTS.md](docs/WHISPER_ARTIFACTS.md).

**Switch mode:**

```bash
# Remote ASR (matches default engine in bundled config.yaml)
VTT2_TRANSCRIPTION_ENGINE=remote_asr uv run python src/vtt2/main.py

# Local MLX on Mac — downloads model, ~3.5 GB RAM for large-v3
VTT2_TRANSCRIPTION_ENGINE=mlx_whisper uv run python src/vtt2/main.py
```

To use remote ASR, set in `config.yaml`:

```yaml
transcription:
  engine: remote_asr
  remote_asr:
    host: "YOUR_TAILSCALE_IP"  # Tailscale IP of your server
    port: 8001
    path: "/v1/audio/transcriptions"
    model: "cstr/whisper-large-v3-turbo-int8_float32"
```

Or override via env: `VTT2_TRANSCRIPTION_ENGINE=remote_asr`, `LOCAL_AI_ASR_BASE_URL=http://host:8001`.

**Local setup (keep your IP private):** Create `.env.vtt2` (gitignored) before running `--install`. The service will inject these into the launchd plist:

```bash
# .env.vtt2 (copy from .env.vtt2.example)
VTT2_TRANSCRIPTION_ENGINE=remote_asr
LOCAL_AI_ASR_BASE_URL=http://100.x.x.x:8001
```

Then run `uv run python src/vtt2/main.py --install`. After reboot, VTT will use your server automatically.

### Choose a model (local MLX only)

Edit `config.yaml` to pick a model that fits your Mac:

| Model | RAM needed | Quality | Speed |
|---|---|---|---|
| `whisper-tiny-mlx` | 2 GB | Basic | Fastest |
| `whisper-small-mlx` | 4 GB | Good | Fast |
| `whisper-medium-mlx` | 6 GB | Great | Fast |
| `whisper-large-v3-mlx` | 10 GB | Best | Fast |

All models are from [mlx-community](https://huggingface.co/mlx-community) on Hugging Face. The full model name uses the prefix `mlx-community/`, for example:

```yaml
transcription:
  mlx_whisper:
    model_name: "mlx-community/whisper-large-v3-mlx"
```

Default is `whisper-large-v3-mlx` (best quality). If you have 8 GB RAM, use `whisper-medium-mlx`.

### Configuration

All settings are in `config.yaml`. Shape (simplified):

```yaml
stt_server:
  host: "127.0.0.1"
  port: 8765
  engine: mlx_whisper          # model owner (LaunchAgent ai.vtt2.stt)

transcription:
  engine: local_stt            # menubar → HTTP client
  local_stt:
    base_url: "http://127.0.0.1:8765"
  mlx_whisper:
    model_name: "mlx-community/whisper-large-v3-mlx"
    language: "auto"  # or "en", "ru", "zh", "ja", …

audio:
  max_recording_duration: 7200  # seconds (2 hours)

ui:
  hotkey: "option+space"
  auto_paste_enabled: true

text_processing:
  strip_whisper_tail_artifacts: true
  whisper_artifact_languages: [ru, en]
```

You can also override settings with environment variables using the `VTT2_` prefix (see `.env.example`). Agent-facing API details: [docs/STT_API.md](docs/STT_API.md).

### Troubleshooting

**Hotkey not working:**
Add your terminal app to System Settings > Privacy & Security > Accessibility and Input Monitoring. Restart the app.

**STT not ready / menubar fails to transcribe:** Wait for `curl -fsS http://127.0.0.1:8765/readyz`. Check `~/Library/Logs/vtt2/stt.stderr.log`. Reload: `launchctl unload ~/Library/LaunchAgents/ai.vtt2.stt.plist && launchctl load ~/Library/LaunchAgents/ai.vtt2.stt.plist`.

**Hotkey stopped responding after recording (stuck):** Restart the UI service: `launchctl unload ~/Library/LaunchAgents/ai.vtt2.plist && launchctl load ~/Library/LaunchAgents/ai.vtt2.plist`. If a zombie remains, `pkill -9 -f 'src/vtt2/main.py'` (careful: also stops STT if matching), remove `~/.local/state/vtt2/vtt2.pid`, then `--install` or load plists again.

**"Model not found" on first run:**
The model downloads from Hugging Face on first STT warmup. Need internet once; then offline.

**High memory usage:**
- Default: one MLX resident in `ai.vtt2.stt` (~3.5 GB); menubar stays light.
- Do not set menubar `engine: mlx_whisper` while STT is also running (second copy).
- Or use `remote_asr` / a smaller `mlx_whisper` model.

**Check everything at once:**
```bash
uv run python src/vtt2/main.py --health
uv run python src/vtt2/main.py --status
curl -fsS http://127.0.0.1:8765/readyz
```

### Logs

Logs are at `~/Library/Logs/vtt2/`:

- Menubar: `vtt2.stdout.log`, `vtt2.stderr.log`, `vtt2.log`
- STT API: `stt.stdout.log`, `stt.stderr.log`

For verbose output: `uv run python src/vtt2/main.py --verbose`

### Supported languages

Whisper supports 99 languages including English, Russian, Chinese, Japanese, Spanish, French, German, Arabic, Hindi, and many more. Set `language: "auto"` in config (default) and it detects automatically.

### Development

```bash
# Run tests
uv run pytest

# Benchmark transcription speed
uv run python test_transcription_speed.py
```

### License

MIT

---

Built with [MLX](https://github.com/ml-explore/mlx) by Apple.
