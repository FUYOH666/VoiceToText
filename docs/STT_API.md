# Local STT HTTP API (for agents)

OpenAI-compatible speech-to-text on loopback. **One process owns the ASR model** (`ai.vtt2.stt`). The default checkpoint is Qwen3-ASR 1.7B 8-bit. The menubar app (`ai.vtt2`) and any agent (OpenClaw, scripts, bots) are HTTP clients — they do not load MLX again.

## Base URL

```
http://127.0.0.1:8765
```

Bind is loopback only. No auth on localhost. Do not expose this port to LAN without adding your own auth.

## Config profiles

| File | Behavior |
|------|----------|
| [`config.yaml`](../config.yaml) (**default**) | `preload_on_start: false`, `idle_unload_seconds: 900`, `engine: qwen3_asr`, `moona3k/mlx-qwen3-asr-1.7b-8bit`, language `ru` — model loads on first request, unloads after 15 min idle |
| [`config.resident.yaml`](../config.resident.yaml) | Same Qwen checkpoint, always loaded (`idle_unload_seconds: 0`) |
| [`config.qwen.yaml`](../config.qwen.yaml) | Clean copy of the idle Qwen default |

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
| `GET` | `/healthz` | Process alive (`200`). Includes `ready`, `loading`, `last_error`, `active_jobs`, `queued`, `idle_unload_seconds` |
| `GET` | `/readyz` | Model loaded (`200`); else `503` (idle / not yet loaded / loading) |
| `POST` | `/v1/audio/transcriptions` | Transcribe; **loads model on demand** if unloaded |
| `GET` | `/v1/models` | Model catalog: installed, active, recommended for this Mac's memory |
| `POST` | `/v1/models/{id}/download` | Start a background download (`202`); dictation keeps working |
| `GET` | `/v1/models/{id}/download` | Download progress |
| `POST` | `/v1/models/{id}/activate` | Switch the loaded model; persisted in user settings |
| `DELETE` | `/v1/models/{id}` | Remove the model from the Hugging Face cache |
| `POST` | `/v1/models/custom` | `{"repo": "org/name"}`: check a Hugging Face repo and add it to the list |

### Models

The catalog lives in `src/vtt2/model_catalog/catalog.yaml`: quantized MLX checkpoints first (Qwen3-ASR 1.7B/0.6B 8-bit, Whisper large-v3 / turbo in 8-bit and 4-bit, fp16 for maximum quality, Whisper small as the minimum). Each entry has its download size, approximate memory while loaded (`ram_gb`; unified memory on a Mac) and `min_memory_gb`.

`GET /v1/models` returns `{"object": "list", "data": [...], "system_memory_gb", "recommended", "active"}`. Each model has `id, title, family, repo, quantization, download_gb, ram_gb, min_memory_gb, languages, note, installed, active, recommended, fits_memory, custom`, plus `download` while one is running. `recommended` follows the rules at the top of the catalog (16 GB and more → Qwen3-ASR 1.7B 8-bit, less → 0.6B 8-bit). A model set by hand in `config.yaml` that is not in the catalog shows up as `id: "configured"`.

Download progress: `{"model", "state": "idle|queued|downloading|done|error", "bytes_done", "bytes_total", "progress", "error"}`.

Activation runs on the inference worker, so it waits for a running transcription instead of interrupting it. It writes only the selection keys (`stt_server.engine`, `transcription.<family>.model_name`) to `~/Library/Application Support/VoiceToText/config.yaml`, which is layered over the repo `config.yaml` (env `VTT2_*` still wins; `VTT2_USER_DIR` moves the folder). If the new model fails to load, the previous selection stays and nothing is written.

Custom models: MLX Whisper checkpoints (config with `n_mels`/`n_audio_ctx`, as in `mlx-community/whisper-*`) and Qwen3-ASR checkpoints are accepted; anything else is `422 unsupported_model`. They are saved to `models.yaml` next to the user settings with `custom: true`.

| Status | `code` | When |
|--------|--------|------|
| `404` | `model_not_found` | Unknown id, or the Hugging Face repo does not exist |
| `409` | `model_not_installed` | Activate before downloading |
| `409` | `model_downloading` | Activate or delete while it downloads |
| `409` | `model_active` | Delete the model that is in use |
| `422` | `unsupported_model` | Custom repo is not an MLX Whisper / Qwen3-ASR checkpoint |
| `429` | `busy` | Switching while the queue is full |
| `500` | `model_load_failed` | The new model did not load; the previous one stays selected |

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

### Errors

Every error is JSON in the OpenAI shape. The top-level `detail` repeats `error.message` for clients written against older versions:

```json
{
  "error": {
    "message": "STT busy: another transcription is running",
    "type": "rate_limit_error",
    "param": null,
    "code": "busy"
  },
  "detail": "STT busy: another transcription is running"
}
```

Clients decide on `status` and `error.code`, never on the message text:

| Status | `code` | Meaning | Client retries? |
|---|---|---|---|
| 400 | `invalid_audio` | Empty file, or the audio cannot be decoded | no |
| 400 | `unsupported_language` | `language` is not a code such as `en` or `auto` (for example `Thai`) | no |
| 400 | `invalid_request` | Bad `response_format`, `prompt` over 1000 characters, missing `file` | no |
| 413 | `file_too_large` | Body over `stt_server.max_upload_mb` | no |
| 413 | `audio_too_long` | Decoded audio over `stt_server.max_audio_seconds` | no |
| 429 | `busy` | The model was busy for the whole `queue_timeout_seconds`. Has a `Retry-After` header (seconds) | yes, after `Retry-After` |
| 503 | `model_loading` | The model is still loading. Has a `Retry-After` header | yes, after `Retry-After` |
| 500 | `model_load_failed` | Loading the model failed. `/healthz` shows `last_error`. The next request tries the load again | no |
| 500 | `transcription_failed` | The engine raised during inference | no |
| 504 | `transcription_timeout` | Inference ran past `request_timeout_seconds` | no |

`error.type` is `invalid_request_error` for 4xx (except 429), `rate_limit_error` for 429 and `server_error` for 5xx.

A 504 does not stop the inference: MLX cannot be interrupted, so the job keeps the model until it really finishes. While it runs, new requests wait in the queue and may get `429 busy`. A 500 or 504 means the same file is likely to fail again; show the error and let the user decide.

### Limits and queue

- **Upload size:** `stt_server.max_upload_mb` (default 80). A larger `Content-Length` is rejected with `413` before the body is read. A chunked body is counted while it streams and cut off at the limit. 80 MB is headroom for about 20 minutes of 16 kHz mono 16-bit WAV (~38 MB). It is not a promise that every 20-minute file fits: a 48 kHz PCM WAV can be larger than 80 MB.
- **Audio length:** `stt_server.max_audio_seconds` (default 1800, 30 minutes). Checked after decoding.
- **Inference timeout:** `stt_server.request_timeout_seconds` (default 1200). A first model load that runs longer returns `503 model_loading`.
- **Queue:** one inference at a time, on one dedicated thread that owns the model. A request waits for the model up to `stt_server.queue_timeout_seconds` (default 120), then gets `429 busy` (or `503 model_loading` if the model is still loading). Clips under 60 seconds (dictation) go ahead of longer queued jobs, so Option+Space waits for at most the job already running, not for every agent file in the queue.
- **Idle unload** never runs while a job is active, including a job whose request already got a 504.

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

## Default engine: Qwen3-ASR

Default `stt_server.engine` is `qwen3_asr`. Qwen is the same process, not a second port and not a second model in memory. The menubar still posts the file to `127.0.0.1:8765`. Menu items **Whisper** and **Qwen** change `stt_server.engine` in `config.yaml` (and add a `qwen3_asr` block the first time) and restart only `ai.vtt2.stt`. A click during recording is ignored. If the extra is missing, the file is left as it was and a server started with this default exits instead of falling back to Whisper.

`config.yaml` sets `moona3k/mlx-qwen3-asr-1.7b-8bit` with `quantization_bits: null`. That checkpoint is already 8-bit, group 64, for `mlx-qwen3-asr` (about 2 GB). The process loads it as stored and does not quantize again. It is not an `mlx-community` / `mlx-audio` quant. Official float weights remain `Qwen/Qwen3-ASR-1.7B` with `quantization_bits: 8`. On this Mac the first request downloaded that snapshot and answered a 3-second clip in 43 seconds; the same clip with the model already loaded took 0.22 seconds. After idle unload the next request reads the snapshot again.

```bash
uv sync --extra qwen
launchctl kickstart -k "gui/$(id -u)/ai.vtt2.stt"
```

Ordinary `uv sync` does not install the extra. If the config selects Qwen and the extra is missing, the process exits with `uv sync --extra qwen`. It does not fall back to Whisper.

Until kickstart, the port keeps serving the model already loaded. Omitted or blank `language` still uses the profile language (`qwen3_asr.language`, default `ru`). `language=auto` is library autodetect. A canonical code is passed through; names such as `Thai` stay `400`.

Segment times come from the library's chunks. Word timestamps are requested the same way as for Whisper and load the library's forced aligner for that request only.

Whisper is the menu item. It rewrites `stt_server.engine` to `mlx_whisper` and restarts only `ai.vtt2.stt`. The Whisper block stays in `config.yaml`.

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
agent / menubar  →  POST 127.0.0.1:8765  →  one model (qwen3_asr by default; Whisper from the menu)
```

Tail-artifact stripping runs on the server for every segment, then the top-level `text` is rebuilt.
