# VTT MLX

**Voice-to-text that runs entirely on your Mac.** No cloud, no subscription, no internet after setup.

Press **Option+Space**, speak, and the transcribed text appears where your cursor is.

## How it works

1. Press **Option+Space** to start recording
2. Speak (any language -- auto-detected)
3. Press **Option+Space** again to stop
4. Text is transcribed locally and pasted into the active app

Powered by [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) on Apple Silicon. Runs ~42x faster than real-time on M4 Max.

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

## Choose a model

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
Switch to a smaller model in `config.yaml` (see table above). Memory auto-cleanup is enabled by default.

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
