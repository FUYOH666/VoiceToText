# Security

VoiceToText is designed to keep speech on the user's Mac:

- The STT server binds to `127.0.0.1` only and refuses other hosts.
- Recordings, history and settings live in `~/Library/Application Support/VoiceToText/`; transcripts are not written to logs.
- The network is used only to download dependencies and models (Hugging Face). There is no telemetry.
- The app needs only Microphone and Accessibility (to paste). It does not use the camera or Input Monitoring.

## Reporting a vulnerability

Please report security issues privately to [private@scanovich.ai](mailto:private@scanovich.ai) rather than in a public issue. Include steps to reproduce and the version (`menu → О программе` or `CHANGELOG.md`). You will get a reply within a few days.
