# Local STT HTTP API (for agents)

OpenAI-compatible speech-to-text on loopback. **One process owns the Whisper model** (`ai.vtt2.stt`). The menubar app (`ai.vtt2`) and any agent (OpenClaw, scripts, bots) are HTTP clients — they do not load MLX again.

## Base URL

```
http://127.0.0.1:8765
```

Bind is loopback only. No auth on localhost. Do not expose this port to LAN without adding your own auth.

## Endpoints

| Method | Path | Meaning |
|--------|------|---------|
| `GET` | `/healthz` | Process alive (`200`) |
| `GET` | `/readyz` | Model loaded and accepting work (`200`); else `503` |
| `POST` | `/v1/audio/transcriptions` | Transcribe uploaded audio |

### Transcription

Multipart form:

- `file` (required) — audio (`wav`, `flac`, …; `ogg`/`webm`/`m4a` via `ffmpeg` if installed)
- `language` (optional) — hint, logged
- `model` (optional) — logged; server uses `config.yaml` model

Response (minimum):

```json
{"text": "…"}
```

HTTP codes: `400` bad/empty audio, `413` file too large, `503` not ready / busy, `500` internal.

Max upload size: `stt_server.max_upload_mb` (default 25). Concurrency: 1.

## Examples

```bash
# Wait until model is warm (after login / --install)
curl -fsS http://127.0.0.1:8765/readyz

curl -fsS -F file=@sample.ogg http://127.0.0.1:8765/v1/audio/transcriptions
# → {"text":"..."}
```

OpenAI-style clients: set base URL to `http://127.0.0.1:8765` and use the audio transcriptions endpoint (same path as Whisper API).

## Lifecycle

```bash
uv run python src/vtt2/main.py --install    # ai.vtt2.stt + ai.vtt2
uv run python src/vtt2/main.py --status
uv run python src/vtt2/main.py --serve-stt  # foreground debug
```

Logs: `~/Library/Logs/vtt2/stt.stdout.log`, `stt.stderr.log`.

Config: `stt_server` + `transcription.mlx_whisper` in [`config.yaml`](../config.yaml). Menubar uses `transcription.engine: local_stt`.

## Architecture note

```
agent / menubar  →  POST 127.0.0.1:8765  →  mlx_whisper (resident)
```

Whisper tail-artifact stripping runs on the server so all clients get the same text.
