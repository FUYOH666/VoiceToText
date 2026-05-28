# Troubleshooting

## `remote_asr_engine` in the log but I want local MLX

**Cause:** Old process still running, or wrong profile (`mac-m1-remote`).

**Fix:**

1. Quit VTT2 (Ctrl+C or menu-bar quit).
2. Confirm [config.yaml](../config.yaml): `active_profile: mac-m1-local`.
3. Restart:

   ```bash
   ./.venv/bin/python src/vtt2/main.py --profile mac-m1-local
   ```

4. At startup you should see: `engine=mlx_whisper` and model `mlx-community/whisper-large-v3-turbo-q4`.

## Remote ASR URL not configured

**Cause:** Profile `mac-m1-remote` / `mac-m4-remote` / `linux-f9-edge` without `.env.local`.

**Fix:**

```bash
cp .env.example .env.local
# Set LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
```

Not required for `mac-m1-local` or `mac-m4-local`.

## Transcription hangs or never finishes

**Cause:** Remote ASR server offline (Tailscale) or wrong engine.

**Fix:**

```bash
./.venv/bin/python src/vtt2/main.py --profile mac-m1-local --health
```

For remote: `curl -sf "$LOCAL_AI_ASR_BASE_URL/healthz"`.

## `uv sync` fails on `rumps` / packaging

**Cause:** Old Python 3.12 RC or packaging 26.

**Fix:** Use Python 3.12.8+ and:

```bash
uv sync --extra mac --extra local-mlx
```

See [fresh-install workflow](../.github/workflows/fresh-install.yml).

## Linux F9 points to wrong ASR host

**Cause:** `.env.local` with `LOCAL_AI_ASR_BASE_URL` affects only `linux-f9-edge`, not `linux-f9-local` (fixed in 2.1.1).

**Fix:** Use profile `linux-f9-local` for localhost ASR, or `linux-f9-edge` with `.env.local`.

## No text pasted after transcription

**Cause:** Missing Input Monitoring or Accessibility permission.

**Fix:** System Settings → Privacy & Security → grant Terminal (or your app) Microphone, Accessibility, Input Monitoring.
