# Enterprise Edge — installation guide

Deploy VoiceToText in a **closed contour**: audio stays in your network; inference runs on **your** ASR server.

## Architecture

1. **ASR server** — Linux GPU host, port 8001, OpenAI-compatible API ([asr-api.md](../asr-api.md))
2. **Tailscale** — private connectivity between Mac/Linux clients and ASR
3. **Clients** — Mac menu-bar (`mac-m1-remote` / `mac-m4-remote`) or Linux F9 (`linux-f9-edge`)

## Server checklist

- [ ] ASR service running; `GET /healthz` → 200
- [ ] Model loaded (e.g. Whisper large v3 turbo)
- [ ] Firewall allows Tailscale interface only (recommended)

## Client checklist (Mac)

```bash
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync --extra mac
cp .env.example .env.local
# Edit LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
vtt doctor --profile mac-m1-remote
vtt mac run --profile mac-m1-remote
```

Grant macOS: Microphone, Accessibility, Input Monitoring.

## Client checklist (Linux desktop)

```bash
export PYTHONPATH=clients/linux/src:src/vtt2:src
vtt linux run --profile linux-f9-edge --health
vtt linux run --profile linux-f9-edge
```

## Support profile names

Use exact profile ids from `vtt profiles list` — they map to sales SKUs (M1 remote, M4 local, etc.).

See also [ENTERPRISE_EDGE.md](../ENTERPRISE_EDGE.md).
