# Product matrix

VoiceToText supports **Mac menu-bar (VTT2)** and **Linux F9** clients. Inference is either **local (MLX on Mac)** or **remote (private ASR server)**.

## Mac profiles (VTT2)

| Profile | Hardware | Engine | RAM (typical) |
|---------|----------|--------|---------------|
| `mac-m1-local` | M1 8GB | `mlx_whisper` (turbo-q4) | ~4 GB |
| `mac-m1-remote` | M1 8GB | `remote_asr` | ~120 MB |
| `mac-m4-local` | M4 128GB | `mlx_whisper` (large-v3) | up to 16 GB limit |
| `mac-m4-remote` | M4 | `remote_asr` | ~120 MB |

### Usage

```bash
# Default from config.yaml active_profile (mac-m1-remote)
uv run python src/vtt2/main.py

# Explicit profile
VTT2_PROFILE=mac-m4-local uv run python src/vtt2/main.py
uv run python src/vtt2/main.py --profile mac-m1-remote --health
```

Remote profiles require `.env.local` (gitignored):

```bash
LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
LOCAL_AI_ASR_TIMEOUT=60
```

## Linux profiles (F9)

| Profile | ASR location |
|---------|----------------|
| `linux-f9-local` | Same machine (`127.0.0.1:8001`) |
| `linux-f9-edge` | GPU server in Tailnet (env URL) |

See [clients/linux/README.md](../clients/linux/README.md).

## Configuration layers

1. `config/base.yaml` — shared defaults (no secrets)
2. `config/profiles/<name>.yaml` — hardware / engine overlay
3. `.env.local` — `LOCAL_AI_ASR_*` (not committed)
4. `VTT2_*` environment overrides

## Branches

| Branch | Purpose |
|--------|---------|
| `product-unified` | Active development (this matrix) |
| `mlx-v1.1` | Legacy Mac line |
| `main` | Legacy monorepo (Linux source) |

See [LEGACY_BRANCHES.md](../LEGACY_BRANCHES.md).
