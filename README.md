# VoiceToText

[![CI](https://github.com/FUYOH666/VoiceToText/actions/workflows/ci.yml/badge.svg)](https://github.com/FUYOH666/VoiceToText/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/FUYOH666/VoiceToText)](https://github.com/FUYOH666/VoiceToText/releases)

**Free, private voice-to-text** for macOS (menu bar) and Linux (F9).  
Press a hotkey, speak, get text in any app — **no account, no cloud** when using local MLX on Apple Silicon.

[Русский README](README.ru.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Contributing](CONTRIBUTING.md)

Default branch: `product-unified` ([legacy branches](LEGACY_BRANCHES.md)).

---

## 3 minutes to first text (Mac M1, local)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync --extra mac --extra local-mlx
uv run python scripts/prefetch_mlx_model.py   # optional: download MLX model once
./.venv/bin/python src/vtt2/main.py
```

Press **Option+Space** to record; Whisper runs **on your Mac** (MLX q4 turbo); text is pasted into the active app.

After changing `config.yaml`, **restart** the app. Startup log must show `engine=mlx_whisper`, not `remote_asr_engine`.

---

## Run from Terminal (Mac)

```bash
cd VoiceToText
./.venv/bin/python src/vtt2/main.py                    # default: mac-m1-local
./.venv/bin/python src/vtt2/main.py --profile mac-m1-local --health
```

Stop with **Ctrl+C** or quit from the menu-bar icon.

---

## Enterprise: remote ASR (optional)

For a **private ASR server** (your GPU, Tailscale):

```bash
cp .env.example .env.local
# LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
./.venv/bin/python src/vtt2/main.py --profile mac-m1-remote
```

`.env.local` is **not** required for `mac-m1-local` / `mac-m4-local`.  
See [Enterprise Edge](docs/ENTERPRISE_EDGE.md) · [Install guide](docs/enterprise/INSTALL.md).

---

## Profiles

| Profile | Use case |
|---------|----------|
| `mac-m1-local` | M1 offline MLX, turbo-q4 (**default**) |
| `mac-m1-remote` | M1 → private ASR |
| `mac-m4-local` | M4 offline MLX (large-v3) |
| `mac-m4-remote` | M4 → private ASR |
| `linux-f9-local` | Linux F9 → localhost ASR |
| `linux-f9-edge` | Linux F9 → ASR on Tailnet |

Details: [Product matrix](docs/PRODUCT_MATRIX.md)

---

## Dependencies

| Setup | Command |
|-------|---------|
| Mac + local MLX | `uv sync --extra mac --extra local-mlx` |
| Mac + remote only | `uv sync --extra mac` |
| Linux F9 | `uv sync` |

## Configuration

1. `config/base.yaml` — shared defaults (no secrets)
2. `config/profiles/<profile>.yaml` — engine tuning
3. `config.yaml` — `active_profile`
4. `.env.local` — ASR URL for **remote profiles only** (gitignored)

## Linux F9

[clients/linux/README.md](clients/linux/README.md)

## macOS permissions

Microphone, Accessibility (hotkey), Input Monitoring (paste).

## Unified CLI

```bash
vtt profiles list
vtt validate-config
vtt doctor
vtt mac run --profile mac-m1-local
```

## Development

```bash
uv sync --extra dev --extra mac --extra local-mlx
uv run pytest
```

## Docs

- [Golden standard](docs/GOLDEN_STANDARD.md) · [ASR API](docs/asr-api.md)
- [Roadmap](docs/ROADMAP.md) · [Technical debt](docs/TECH_DEBT.md)

## License

MIT — use freely, no telemetry by design for local profiles.
