# VTT MLX

**Voice-to-text on your Mac.** Local or remote — your choice.

Press **Option+Space**, speak, and the transcribed text appears where your cursor is.

**Two modes:**

| Mode | RAM on Mac | Where it runs |
|------|------------|---------------|
| `mlx_whisper` (local) | ~3.5 GB | Your Mac (Apple Silicon) |
| `remote_asr` | **~120 MB** | Linux GPU server via Tailscale |

With `remote_asr`, the model runs on your server — Mac stays light. Lazy imports ensure MLX is never loaded when using remote.

**Switch mode:**

```bash
# Local on Mac (default)
VTT2_TRANSCRIPTION_ENGINE=mlx_whisper uv run python src/vtt2/main.py

# Remote via Tailscale — saves ~3 GB RAM
VTT2_TRANSCRIPTION_ENGINE=remote_asr uv run python src/vtt2/main.py
```

## How it works

1. Press **Option+Space** to start recording
2. Speak (any language — auto-detected)
3. Press **Option+Space** again to stop
4. Text is transcribed and pasted into the active app

**Local mode:** [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon — ~42x faster than real-time on M4 Max.  
**Remote mode:** Whisper on your Linux GPU server via Tailscale.

## Requirements

- Mac with Apple Silicon (M1, M2, M3, M4 -- any variant)
- macOS 13+ (Ventura or later)
- 8 GB RAM minimum (see [model selection](#choose-a-model) below)
- [uv](https://docs.astral.sh/uv/) package manager

## Install

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and set up
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
uv sync
```

The Whisper model downloads automatically on first use (~6 GB for large-v3). After that, everything works offline.

## Run

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

## macOS permissions

On first launch macOS will ask for three permissions. **All three are required:**

| Permission | Why | Where to grant |
|---|---|---|
| Microphone | Record your voice | Privacy & Security > Microphone |
| Accessibility | Global hotkey (Option+Space) | Privacy & Security > Accessibility |
| Input Monitoring | Auto-paste text (Cmd+V) | Privacy & Security > Input Monitoring |

If hotkeys don't work, add your terminal app (Terminal, iTerm, Cursor) to **Accessibility** and **Input Monitoring**, then restart the app.

## Transcription engines

**Local (default):** `mlx_whisper` — runs on your Mac, uses ~3.5 GB RAM + GPU.

**Remote:** `remote_asr` — sends audio to a Linux GPU server via Tailscale. **~120 MB RAM** on Mac (model stays on server). Lazy imports: MLX is never loaded when using remote.

To use remote ASR, set in `config.yaml`:

```yaml
transcription:
  engine: remote_asr
  remote_asr:
    host: "YOUR_TAILSCALE_IP"  # Tailscale IP вашего сервера
    port: 8001
    path: "/v1/audio/transcriptions"
    model: "cstr/whisper-large-v3-turbo-int8_float32"
```

Or override via env: `VTT2_TRANSCRIPTION_ENGINE=remote_asr`, `LOCAL_AI_ASR_BASE_URL=http://host:8001`.

**Local setup (keep your IP private):** Do not commit your Tailscale IP. Use environment variables:

```bash
export VTT2_TRANSCRIPTION_ENGINE=remote_asr
export VTT2_TRANSCRIPTION_REMOTE_ASR_HOST=100.x.x.x  # your Tailscale IP
uv run python src/vtt2/main.py
```

For the launchd service, add `EnvironmentVariables` to `~/Library/LaunchAgents/ai.vtt2.plist` (see `--install`), or create a `.env` and source it before the service starts.

## Choose a model (local MLX only)

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

## Configuration

All settings are in `config.yaml`:

```yaml
# Language: "auto" detects automatically, or set "en", "ru", "zh", "ja", etc.
language: "auto"

# Hotkey
hotkey: "option+space"

# Auto-paste transcribed text into the active app
auto_paste_enabled: true

# Max recording length (seconds)
max_recording_duration: 7200  # 2 hours
```

You can also override settings with environment variables using the `VTT2_` prefix (see `.env.example`).

## Troubleshooting

**Hotkey not working:**
Add your terminal app to System Settings > Privacy & Security > Accessibility and Input Monitoring. Restart the app.

**"Model not found" on first run:**
The model downloads from Hugging Face on first use. Make sure you have internet for the initial download. After that, everything works offline.

**High memory usage:**
- **Best option:** switch to `remote_asr` in `config.yaml` — drops from ~3.5 GB to ~120 MB (model runs on server).
- Or use a smaller local model (see table above). Memory auto-cleanup is enabled by default.

**Check everything at once:**
```bash
uv run python src/vtt2/main.py --health
```

## Logs

Logs are at `~/Library/Logs/vtt2/vtt2.log` (auto-rotated, 10 MB max).

For verbose output: `uv run python src/vtt2/main.py --verbose`

## Supported languages

Whisper supports 99 languages including English, Russian, Chinese, Japanese, Spanish, French, German, Arabic, Hindi, and many more. Set `language: "auto"` in config (default) and it detects automatically.

## Development

```bash
# Run tests
uv run pytest

# Benchmark transcription speed
uv run python test_transcription_speed.py
```

## License

MIT

---

Built with [MLX](https://github.com/ml-explore/mlx) by Apple.
