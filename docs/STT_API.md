# Local STT HTTP API (for agents)

OpenAI-compatible speech-to-text on loopback. **One process owns the Whisper model** (`ai.vtt2.stt`). The menubar app (`ai.vtt2`) and any agent (OpenClaw, scripts, bots) are HTTP clients — they do not load MLX again.

## Base URL

```
http://127.0.0.1:8765
```

Bind is loopback only. No auth on localhost. Do not expose this port to LAN without adding your own auth.

## Config profiles

| File | Behavior |
|------|----------|
| [`config.yaml`](../config.yaml) (**default**) | `preload_on_start: false`, `idle_unload_seconds: 900`, `mlx_whisper.language: ru` — model loads on first request, unloads after 15 min idle |
| [`config.resident.yaml`](../config.resident.yaml) | Always-on snapshot — model stays loaded after warmup (`idle_unload_seconds: 0`) |

Switch to resident:

```bash
cp config.resident.yaml config.yaml
uv run python src/vtt2/main.py --install
```

Switch back to idle-unload (default in repo):

```bash
# restore idle profile from git, or keep your edited config.yaml
git checkout -- config.yaml   # only if you have no local edits you need
uv run python src/vtt2/main.py --install
```

## Endpoints

| Method | Path | Meaning |
|--------|------|---------|
| `GET` | `/healthz` | Process alive (`200`). Includes `ready`, `loading`, `idle_unload_seconds` |
| `GET` | `/readyz` | Model loaded (`200`); else `503` (idle / not yet loaded / loading) |
| `POST` | `/v1/audio/transcriptions` | Transcribe; **loads model on demand** if unloaded |

### Transcription

Same URL for menubar and agents. Default response stays `{"text":"…"}` so existing clients do not break. Long jobs (up to ~10 minutes) use native Whisper windowing with correct segment offsets.

Multipart form:

- `file` (required) — audio (`wav`, `flac`, …; `ogg`/`webm`/`m4a` via `ffmpeg` if installed)
- `language` (optional) — hint, logged
- `model` (optional) — logged; server uses `config.yaml` model
- `response_format` (optional) — `json` (default), `verbose_json`, `text`
- `timestamp_granularities` / `timestamp_granularities[]` (optional) — include `word` for word-level timings (only in `verbose_json`)

Default JSON (menubar / simple clients):

```json
{"text": "…"}
```

`response_format=verbose_json` (agents that need timecodes):

```json
{
  "task": "transcribe",
  "language": "ru",
  "duration": 612.3,
  "text": "…",
  "segments": [
    {"id": 0, "start": 0.0, "end": 4.2, "text": "…"}
  ]
}
```

With `timestamp_granularities=word`, a segment may also include `"words": [{"word":"…","start":0.0,"end":0.4}]`.

`response_format=text` returns plaintext (`text/plain`), not JSON.

HTTP codes: `400` bad/empty audio or invalid `response_format`, `413` file too large, `503` load failed / busy / timeout, `500` internal.

Max upload size: `stt_server.max_upload_mb` (default 40 — enough for ~10 min 16 kHz WAV). Request timeout: `stt_server.request_timeout_seconds` (default 600). **Concurrency: 1** — a 10 minute job blocks Option+Space until it finishes.

**Idle unload:** after `idle_unload_seconds` without requests the server drops weights (`readyz` → 503). The next `POST` loads again (cold start; menubar waits up to `local_stt.warmup_wait_seconds`).

## Examples

```bash
# Process up (model may be unloaded)
curl -fsS http://127.0.0.1:8765/healthz

# May be 503 when idle — that is OK with default profile
curl -sS http://127.0.0.1:8765/readyz || true

# Default: {"text":"..."}  (menubar / simple clients)
curl -fsS -F file=@sample.ogg http://127.0.0.1:8765/v1/audio/transcriptions

# Full transcript + segment timecodes (agents, ~10 min audio)
curl -fsS \
  -F file=@meeting.wav \
  -F response_format=verbose_json \
  http://127.0.0.1:8765/v1/audio/transcriptions

# Optional word-level timings (OpenAI-style field name)
curl -fsS \
  -F file=@meeting.wav \
  -F response_format=verbose_json \
  -F 'timestamp_granularities[]=word' \
  http://127.0.0.1:8765/v1/audio/transcriptions
```

OpenAI-style clients: set base URL to `http://127.0.0.1:8765` and use the audio transcriptions endpoint. Prefer `POST` over assuming `readyz` is always green when using idle-unload. For timestamps, set `response_format="verbose_json"`.

## Lifecycle

```bash
uv run python src/vtt2/main.py --install    # ai.vtt2.stt + ai.vtt2
uv run python src/vtt2/main.py --status
uv run python src/vtt2/main.py --serve-stt  # foreground debug

# After pulling a new STT version, restart the model process (menubar can stay)
launchctl kickstart -k "gui/$(id -u)/ai.vtt2.stt"
```

Logs: `~/Library/Logs/vtt2/stt.stdout.log`, `stt.stderr.log`.

## Architecture note

```
agent / menubar  →  POST 127.0.0.1:8765  →  mlx_whisper (load ↔ idle unload)
```

Whisper tail-artifact stripping runs on the server so all clients get the same text (last segment, then rejoined `text`).
