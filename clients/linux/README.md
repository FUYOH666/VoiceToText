# Linux F9 client

Voice-to-text hotkey client (F9) for Linux desktops. Copied from legacy `main` → `platforms/linux`.

## Profiles (repo root)

Configuration uses **F9 schema** (`asr.*`), not Mac `transcription.*`:

| Profile | ASR URL |
|---------|---------|
| `linux-f9-local` | `http://127.0.0.1:8001` |
| `linux-f9-edge` | `LOCAL_AI_ASR_BASE_URL` in `.env.local` |

```bash
# From repository root
export VTT2_PROFILE=linux-f9-local
export PYTHONPATH=src:clients/linux/src
cd clients/linux
uv run python -m f9_asr.main
```

See [docs/PRODUCT_MATRIX.md](../../docs/PRODUCT_MATRIX.md) and profile YAML in `config/profiles/linux-f9-*.yaml`.

## Shared ASR HTTP client

`f9_asr/asr_client.py` delegates to `vtt_asr_client` (same package as Mac `remote_asr`).
