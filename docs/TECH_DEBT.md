# Technical debt register — product-unified

Living document. Severity: **P0** (blocker), **P1** (soon), **P2** (nice).

## Resolved in 2.1.1

| ID | Was | Fix |
|----|-----|-----|
| SR-ENV-1 | F9 `.env.local` overwrote `linux-f9-local` | `LOCAL_AI_ASR_*` only for `linux-f9-edge` |
| TD-DEFAULT | Default profile `mac-m1-remote` | `mac-m1-local` in config.yaml + loader |
| TD-STARTUP-LOG | Hard to see active engine | Log profile/engine/model at startup |
| TD-MLX-IMPORT | MLX loaded for remote | Lazy import in `TranscriptionEngineWrapper` (already OK) |

## Resolved in 2.1.0 (Golden Standard)

| ID | Was | Fix |
|----|-----|-----|
| TD-CONFIG | Single `config.yaml` drift | `config/profiles/*` |
| TD-SECRET | Tailscale IP in git | `.env.local` |
| TD-DUP-ASR | Duplicate HTTP client | `vtt_asr_client` |
| TD-F9-CONFIG | F9 separate yaml | `F9Config.from_profile()` |
| TD-VERSION | yaml vs pyproject | `scripts/sync_version.py` |
| TD-ARTIFACTS | Missing whisper tail strip | `whisper_artifacts.py` |
| TD-CI | No GitHub Actions | `ci.yml` |
| TD-UV-RUMPS | rumps breaks Linux CI | `mac` optional extra |

## Open — P1

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-UV-RUMPS | `uv sync --extra mac` may fail on old Python rc | Fresh install breaks | Python 3.12.8+; `fresh-install.yml` |
| TD-LAUNCHD | launchd lacks microphone | Broken autostart | README: Login Items only |
| TD-LOCK | `clients/linux/uv.lock` + root `uv.lock` | Two dependency worlds | Document or uv workspace |

## Open — P2

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-WHISPER-CPP | whisper.cpp paths in base | Config noise | Move to local profiles only |
| TD-TESTS-ENV | Weak ENV override tests | Contract drift | Stricter asserts |
| TD-PYRIGHT | `clients/linux` not in pyright | IDE noise | Extend include |
| TD-GIF | No demo in README | Discoverability | Screen recording later |

## Architecture decisions (keep)

- Two config schemas: VTT2 vs F9 — intentional.
- No git merge `main` ↔ `mlx-v1.1`.
- ASR GPU server out of repo.

## Review cadence

Update on each release. Target: **2.2.0** = uv workspace or demo GIF.
