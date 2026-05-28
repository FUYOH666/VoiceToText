# Roadmap — VoiceToText

Default branch: **`product-unified`**.

## Done (2.1.0 — Golden Standard)

- [x] Profile-based config (6 profiles)
- [x] `vtt` CLI: doctor, validate-config, mac/linux run
- [x] Shared `vtt_asr_client`
- [x] Whisper tail artifacts + tests
- [x] CI: pytest, IP grep, profile matrix, mock ASR
- [x] Docs: GOLDEN_STANDARD, asr-api, enterprise/INSTALL
- [x] Release v2.1.0, legacy tags, default branch cutover

## Done (2.1.1 — Ship pass)

- [x] F9 env leak fix (`linux-f9-local` vs `.env.local`)
- [x] Default profile `mac-m1-local`
- [x] TROUBLESHOOTING, CONTRIBUTING, SECURITY, issue templates
- [x] README polish + README.ru
- [x] GitHub About / topics update

## Next (2.2.x)

| Item | Why |
|------|-----|
| Demo GIF in README | Onboarding |
| `uv` workspace (single lockfile) | Linux + Mac one install |
| Prefetch MLX in `vtt doctor` | First-run UX |
| GitHub Discussions | Community Q&A |
| Optional local audit log (no telemetry) | Enterprise narrative |

## Enterprise (ongoing)

- Install bundle: [enterprise/INSTALL.md](enterprise/INSTALL.md)
- Private ASR contract: [asr-api.md](asr-api.md)

## Non-goals

- Merge `main` and `mlx-v1.1` histories
- ASR GPU server inside this repo
- Public cloud STT as default
- Telemetry / phone-home
