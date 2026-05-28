# ASR API contract (client ↔ server)

VoiceToText Mac and Linux clients speak to your **private ASR service** via an OpenAI-compatible HTTP API.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/healthz` | Liveness / readiness (must return 200) |
| `POST` | `/v1/audio/transcriptions` | Transcribe audio |

## Transcription request

- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file` — WAV audio (mono, 16 kHz from clients)
  - `model` — model id string (server may ignore; client sends configured name)
  - `language` — optional; omit or `auto` for detection
  - `response_format` — `json` (F9) or default (Mac client)

## Transcription response

**JSON (recommended):**

```json
{
  "text": "transcribed text"
}
```

## Client implementation

Shared library: [`src/vtt_asr_client/`](../src/vtt_asr_client/)

- Mac: `remote_asr` engine
- Linux: `f9_asr.asr_client`

## Configuration

Server base URL is **never** committed. Set:

```bash
LOCAL_AI_ASR_BASE_URL=http://YOUR_TAILSCALE_HOST:8001
```

in `.env.local`.

## Operational check

```bash
curl -sf "${LOCAL_AI_ASR_BASE_URL}/healthz"
vtt doctor --profile mac-m1-remote
```
