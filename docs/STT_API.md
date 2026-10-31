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
| [`config.yaml`](../config.yaml) (**default**) | `preload_on_start: false`, `idle_unload_seconds: 900`, `engine: mlx_whisper`, `mlx_whisper.language: ru` — model loads on first request, unloads after 15 min idle |
| [`config.resident.yaml`](../config.resident.yaml) | Always-on Whisper snapshot — model stays loaded after warmup (`idle_unload_seconds: 0`) |
| [`config.qwen.yaml`](../config.qwen.yaml) | Same idle profile, `engine: qwen3_asr`, pre-quantized `moona3k/mlx-qwen3-asr-1.7b-8bit` |

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

Same URL for menubar and agents. Default response stays `{"text":"…"}` so existing clients do not break. Long jobs use native Whisper windowing with correct segment offsets.

Multipart form:

- `file` (required) — audio (`wav`, `flac`, …; `ogg`/`webm`/`m4a` via `ffmpeg` if installed)
- `language` (optional) — canonical code (`en`, `ru`, `th`, …) or `auto`. Omitted or blank keeps the active profile language (`mlx_whisper.language`, or `qwen3_asr.language` when that engine is selected; default `ru`). `auto` is autodetect. On Whisper that choice is made from the first ≤30 seconds and one language token covers the whole file. An explicit code such as `en` fixes that token and decodes in that language mode; it is the wrong mode for stable mixed-language speech (the model can still occasionally emit another language or code-switch). Full names (`Thai`) are `400`.
- `prompt` (optional) — passed to Whisper as `initial_prompt` (max 1000 characters)
- `model` (optional) — logged; server uses the checkpoint in `config.yaml`. It does not switch models on the fly
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

HTTP codes: `400` bad/empty audio, invalid `response_format`, unknown `language`, or oversized `prompt`; `413` file too large; `503` load failed / busy / timeout; `500` internal.

Max upload size: `stt_server.max_upload_mb` (default 80). That is headroom for about 20 minutes of 16 kHz mono 16-bit WAV (~38 MB). It is not a promise that every 20-minute file fits: a 48 kHz PCM WAV can be larger than 80 MB. Request timeout: `stt_server.request_timeout_seconds` (default 1200). **Concurrency: 1** — a long agent job blocks Option+Space until it finishes.

The inference log line is `requested_language=… effective_language=…` (for example `en`/`en`, `auto`/`None`, omitted/`ru`). A log that only says the form field was received does not mean Whisper used it.

**Idle unload:** after `idle_unload_seconds` without requests the server drops weights (`readyz` → 503). The next `POST` loads again (cold start; menubar waits up to `local_stt.warmup_wait_seconds`).

## Examples

```bash
# Process up (model may be unloaded)
curl -fsS http://127.0.0.1:8765/healthz

# May be 503 when idle — that is OK with default profile
curl -sS http://127.0.0.1:8765/readyz || true

# Default: {"text":"..."}  (menubar / simple clients)
curl -fsS -F file=@sample.ogg http://127.0.0.1:8765/v1/audio/transcriptions

# Full transcript + segment timecodes
curl -fsS \
  -F file=@meeting.wav \
  -F response_format=verbose_json \
  http://127.0.0.1:8765/v1/audio/transcriptions

# Explicit language for this file only (config stays ru for the menubar)
curl -fsS \
  -F file=@meeting.wav \
  -F language=auto \
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

## Optional engine: Qwen3-ASR

Default `stt_server.engine` stays `mlx_whisper`. Qwen is the same process, not a second port and not a second model in memory. The menubar still posts the file to `127.0.0.1:8765`. Menu items **Whisper** and **Qwen** change `stt_server.engine` in `config.yaml` (and add a `qwen3_asr` block the first time) and restart only `ai.vtt2.stt`. A click during recording is ignored. If the extra is missing, the file is left as it was.

`config.qwen.yaml` sets `engine: qwen3_asr` and `moona3k/mlx-qwen3-asr-1.7b-8bit` with `quantization_bits: null`. That checkpoint is already 8-bit, group 64, for `mlx-qwen3-asr` (about 2 GB). The process loads it as stored and does not quantize again. It is not an `mlx-community` / `mlx-audio` quant. Official float weights remain `Qwen/Qwen3-ASR-1.7B` with `quantization_bits: 8`. On this Mac the first request downloaded that snapshot and answered a 3-second clip in 43 seconds; the same clip with the model already loaded took 0.22 seconds. After idle unload the next request reads the snapshot again.

```bash
uv sync --extra dev --extra qwen
cp config.qwen.yaml config.yaml
launchctl kickstart -k "gui/$(id -u)/ai.vtt2.stt"
```

Ordinary `uv sync` does not install the extra. If the config selects Qwen and the extra is missing, the process exits with `uv sync --extra qwen`. It does not fall back to Whisper.

Until kickstart, the port keeps serving the model already loaded. Omitted or blank `language` still uses the profile language (`qwen3_asr.language`, default `ru`). `language=auto` is library autodetect. A canonical code is passed through; names such as `Thai` stay `400`.

Segment times come from the library's chunks. Word timestamps are requested the same way as for Whisper and load the library's forced aligner for that request only.

Back to Whisper (only if `config.yaml` has no local edits you need):

```bash
git checkout -- config.yaml
launchctl kickstart -k "gui/$(id -u)/ai.vtt2.stt"
```

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
agent / menubar  →  POST 127.0.0.1:8765  →  one model (mlx_whisper by default; optional qwen3_asr)
```

Tail-artifact stripping runs on the server for every segment, then the top-level `text` is rebuilt.
