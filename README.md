# VoiceToText (product-unified)

Cross-platform voice-to-text: **Mac menu-bar client (VTT2)** and **Linux F9 client**, with profile-based configuration for M1, M4, local MLX, and private remote ASR.

Branch: `product-unified` (see [LEGACY_BRANCHES.md](LEGACY_BRANCHES.md)).

## Quick start (Mac, remote ASR)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync --extra mac
cp .env.example .env.local
# Edit .env.local: LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
vtt doctor --profile mac-m1-remote
vtt mac run --profile mac-m1-remote
```

Golden standard: [docs/GOLDEN_STANDARD.md](docs/GOLDEN_STANDARD.md)

Press **Option+Space** to record; text is transcribed on your ASR server and pasted into the active app.

## Run from Terminal (Mac)

From the **repository root** (after `uv sync --extra mac` and `.env.local`):

```bash
# Menu-bar app (default profile from config.yaml = mac-m1-remote)
.venv/bin/python src/vtt2/main.py

# Explicit profile + health check (ASR must answer GET /healthz)
.venv/bin/python src/vtt2/main.py --profile mac-m1-remote --health

# Same via unified CLI (needs: uv pip install -e .  or  uv sync --extra mac)
uv run vtt mac run --profile mac-m1-remote
```

One-liner if you are already in the project directory:

```bash
./.venv/bin/python src/vtt2/main.py --profile mac-m1-remote
```

Stop the app with **Ctrl+C** in the terminal (or quit from the menu-bar icon).

## Profiles

| Profile | Use case |
|---------|----------|
| `mac-m1-remote` | M1 thin client → private ASR (default in `config.yaml`) |
| `mac-m1-local` | M1 offline MLX (turbo-q4) |
| `mac-m4-local` | M4 offline MLX (large-v3) |
| `mac-m4-remote` | M4 thin client → private ASR |
| `linux-f9-local` | Linux F9 → localhost ASR |
| `linux-f9-edge` | Linux F9 → ASR on Tailnet |

Details: [docs/PRODUCT_MATRIX.md](docs/PRODUCT_MATRIX.md)  
Enterprise / closed contour: [docs/ENTERPRISE_EDGE.md](docs/ENTERPRISE_EDGE.md)

```bash
VTT2_PROFILE=mac-m4-local uv run python src/vtt2/main.py
uv run python src/vtt2/main.py --profile mac-m1-remote --health
```

## Dependencies

- **Mac menu-bar app:** `uv sync --extra mac`
- **Remote / edge Mac:** no MLX extra
- **Local MLX on Mac:** `uv sync --extra mac --extra local-mlx`
- **Linux F9 only:** `uv sync` (core deps)

## Configuration layers

1. `config/base.yaml` — shared defaults (no secrets)
2. `config/profiles/<profile>.yaml` — engine and hardware tuning
3. `config.yaml` — `active_profile` only
4. `.env.local` — `LOCAL_AI_ASR_BASE_URL` (gitignored)

## Linux F9

See [clients/linux/README.md](clients/linux/README.md).

## macOS permissions

Microphone, Accessibility (hotkey), Input Monitoring (paste) — all required.

## Autostart (Mac)

Prefer **Login Items** with `start-vtt2.app`; launchd often lacks microphone access. See [CHANGELOG.md](CHANGELOG.md).

## Unified CLI

```bash
vtt profiles list
vtt validate-config
vtt doctor
vtt mac run --profile mac-m1-remote
vtt linux run --profile linux-f9-local --health
```

## Development

```bash
uv sync --extra dev --extra mac
uv run pytest
vtt validate-config
```

## Docs

- [Golden standard](docs/GOLDEN_STANDARD.md) · [ASR API contract](docs/asr-api.md)
- [Product matrix](docs/PRODUCT_MATRIX.md) · [Enterprise Edge](docs/ENTERPRISE_EDGE.md)
- [Enterprise install](docs/enterprise/INSTALL.md)
- [Roadmap](docs/ROADMAP.md) · [Technical debt](docs/TECH_DEBT.md) · [Cutover checklist](docs/CUTOVER_CHECKLIST.md)

## Cutover

Before making this branch default: [docs/CUTOVER_CHECKLIST.md](docs/CUTOVER_CHECKLIST.md).

## License

MIT
