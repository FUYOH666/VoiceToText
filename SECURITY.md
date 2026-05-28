# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.1.x   | Yes       |
| 2.0.x   | Best effort on `product-unified` |
| Legacy `mlx-v1.1` / `main` | Frozen (tags `legacy/*`) |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

1. Use GitHub **Private vulnerability reporting** (Security tab), or contact the maintainer privately.
2. Do not include Tailscale IPs, API keys, or audio samples with PII in the report.

## Secrets in the repo

- Never commit `.env.local`, tokens, or internal hostnames.
- Use `.env.example` with placeholders only.
- Before push: `git diff` and ensure no `100.x.x.x` Tailscale addresses.

## Privacy

VoiceToText does not send audio to cloud STT by default when using `mac-*-local` profiles. Remote profiles send audio only to the ASR URL you configure in `.env.local`.
