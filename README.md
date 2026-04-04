# VTT MLX

**Turn speech into text instantly — wherever you work, no cloud, no subscription.**

---

## The Problem

You type notes, emails, docs for hours. Your voice is 3x faster.

Cloud transcription costs $10–20/month and sends your data elsewhere. Built-in dictation is slow, unreliable, and doesn't paste where you need it.

## The Solution

VTT sits in your Mac menu bar. Press **Option+Space**, speak, text appears where your cursor is.

Runs locally on Apple Silicon (offline) or on your own server via Tailscale. No subscription. 99 languages, auto-detected. Works in any app.

## Results

- **Before:** 5 min typing a 2-min voice note, or $20/mo for cloud ASR, or 3.5 GB RAM for local models
- **After:** 2 min voice → instant text. Local mode: ~42x real-time. Remote mode: ~120 MB RAM on Mac (model on your server)

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

With **local** `mlx_whisper`, the model downloads on first use (~6 GB for large-v3); after that, transcription works offline. With **`remote_asr`** (default in this repo’s `config.yaml`), the Mac does not load MLX; transcription needs your ASR server reachable (e.g. via Tailscale).

### Run

```bash
uv run python src/vtt2/main.py
```

A microphone icon appears in your menu bar. Press **Option+Space** to record.

### Run as a background service

To start automatically on login and restart on crash:

```bash
# Install
uv run python src/vtt2/main.py --install

# Check status
uv run python src/vtt2/main.py --status

# Remove
uv run python src/vtt2/main.py --uninstall
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
4. Text is transcribed and pasted into the active app

**Local mode:** [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon — ~42x faster than real-time on M4 Max.  
**Remote mode:** Whisper on your Linux GPU server via Tailscale.

### Transcription engines

| Mode | RAM on Mac | Where it runs |
|------|------------|---------------|
| `mlx_whisper` (local) | ~3.5 GB | Your Mac (Apple Silicon) |
| `remote_asr` | **~120 MB** | Linux GPU server via Tailscale |

With `remote_asr`, the model runs on your server — Mac stays light. Lazy imports ensure MLX is never loaded when using remote.

**Models (defaults in `config.yaml`):**

| Engine | Model / artifact |
|--------|------------------|
| `remote_asr` | `cstr/whisper-large-v3-turbo-int8_float32` (server-side; override via `transcription.remote_asr.model`) |
| `mlx_whisper` | `mlx-community/whisper-large-v3-mlx` |
| `whisper_cpp` | GGML file path, e.g. `models/ggml-medium-q5_0.bin` (`transcription.whisper_cpp.model_path`) |

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
transcription:
  engine: remote_asr  # or mlx_whisper | whisper_cpp
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

You can also override settings with environment variables using the `VTT2_` prefix (see `.env.example`).

### Troubleshooting

**Hotkey not working:**
Add your terminal app to System Settings > Privacy & Security > Accessibility and Input Monitoring. Restart the app.

**Hotkey stopped responding after recording (stuck):** Restart the service: `launchctl unload ~/Library/LaunchAgents/ai.vtt2.plist && launchctl load ~/Library/LaunchAgents/ai.vtt2.plist`. If a zombie process remains, kill it in Activity Monitor (`python … main.py`) or `pkill -9 -f vtt2/main.py`, remove `~/.local/state/vtt2/vtt2.pid`, then load again. (v1.2.1+ uses a safer audio stop to reduce this.)

**"Model not found" on first run:**
The model downloads from Hugging Face on first use. Make sure you have internet for the initial download. After that, everything works offline.

**High memory usage:**
- **Best option:** switch to `remote_asr` in `config.yaml` — drops from ~3.5 GB to ~120 MB (model runs on server).
- Or use a smaller local model (see table above). Memory auto-cleanup is enabled by default.

**Check everything at once:**
```bash
uv run python src/vtt2/main.py --health
```

### Logs

Logs are at `~/Library/Logs/vtt2/` (`vtt2.stdout.log`, `vtt2.stderr.log`, `vtt2.log`).

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
