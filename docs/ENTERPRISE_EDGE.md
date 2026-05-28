# VTT Enterprise Edge (private ASR)

**Value proposition:** speech is captured on employee Macs or Linux desktops, but **Whisper inference runs only on infrastructure you control** — not Google, not a SaaS API.

## Architecture

```text
[ Mac VTT2 ] ──Tailscale──┐
[ Linux F9 ] ──VPN/local─┼──► [ Linux GPU ASR :8001 ]
                          │         OpenAI-compatible API
                          └── Private tailnet / LAN
```

- **Clients** record audio and POST WAV to `/v1/audio/transcriptions`.
- **ASR server** (separate deploy, e.g. `remote-ASR` GPU stack) holds models and GPU.
- **Tailscale** (or LAN) provides connectivity without exposing the service to the public internet.

## Recommended profiles

| Role | Profile |
|------|---------|
| MacBook M1 in the field | `mac-m1-remote` |
| MacBook M4 in the field | `mac-m4-remote` |
| Linux workstation + local GPU | `linux-f9-local` |
| Linux desktop, GPU elsewhere | `linux-f9-edge` |

## Onboarding checklist (small org)

1. Deploy ASR on Linux GPU; confirm `GET /healthz` returns 200.
2. Join machines to the same Tailnet.
3. Distribute `.env.local` template (no IPs in git):

   ```bash
   LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
   LOCAL_AI_ASR_TIMEOUT=60
   ```

4. Install Mac client: `uv sync --extra local-mlx` only if any machine needs **local** MLX; edge-only Macs: `uv sync` without MLX extra.
5. Run `uv run python src/vtt2/main.py --profile mac-m1-remote --health`.

## Security notes

- Do not commit Tailscale IPs or tokens to the repository.
- Use `.env.local` per machine or managed secrets (1Password, etc.).
- Audio leaves the client only to **your** ASR endpoint inside the VPN.

## Compliance narrative

- Data does not transit to third-party cloud STT.
- Model and logs stay on your server.
- Clients are thin; revocable access via VPN membership.
