# VoiceToText (product-unified)

Cross-platform voice-to-text: **Mac menu-bar client (VTT2)** and **Linux F9 client**, with profile-based configuration for M1, M4, local MLX, and private remote ASR.

Branch: `product-unified` (see [LEGACY_BRANCHES.md](LEGACY_BRANCHES.md)).

## Quick start (Mac, remote ASR)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync
cp .env.example .env.local
# Edit .env.local: LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
uv run python src/vtt2/main.py --profile mac-m1-remote --health
uv run python src/vtt2/main.py
```

Press **Option+Space** to record; text is transcribed on your ASR server and pasted into the active app.

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

- **Remote / edge Mac:** `uv sync` (no MLX download)
- **Local MLX on Mac:** `uv sync --extra local-mlx`

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

## Development

```bash
uv run pytest
uv run python src/vtt2/main.py --verbose
```

## Docs

- [Product matrix](docs/PRODUCT_MATRIX.md) · [Enterprise Edge](docs/ENTERPRISE_EDGE.md)
- [Roadmap](docs/ROADMAP.md) · [Technical debt](docs/TECH_DEBT.md) · [Cutover checklist](docs/CUTOVER_CHECKLIST.md)

## Cutover

Before making this branch default: [docs/CUTOVER_CHECKLIST.md](docs/CUTOVER_CHECKLIST.md).

## License

MIT
