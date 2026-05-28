# Technical debt register — product-unified

Living document. Severity: **P0** (blocker), **P1** (soon), **P2** (nice).

## Resolved in 2.1.0 (Golden Standard)

| ID | Was | Fix |
|----|-----|-----|
| TD-CONFIG | Single `config.yaml` drift M1/M4/remote | `config/base.yaml` + `config/profiles/*` |
| TD-SECRET | Tailscale IP in tracked YAML | `.env.local` + placeholder only |
| TD-DUP-ASR | Duplicate HTTP client Mac/Linux | `src/vtt_asr_client` |
| TD-BRANCH | No sandbox for unified product | `product-unified` branch |
| TD-F9-CONFIG | F9 separate yaml | `F9Config.from_profile()` |
| TD-VERSION | yaml vs pyproject drift | `scripts/sync_version.py` |
| TD-ARTIFACTS | Missing whisper tail strip | `whisper_artifacts.py` + tests |
| TD-CI | No GitHub Actions | `ci.yml` + `fresh-install.yml` |
| TD-UV-RUMPS | rumps breaks Linux CI | `mac` optional extra |

## Open — P1

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-UV-RUMPS | `uv sync --extra mac` may fail on old Python rc | Fresh install breaks | Use Python 3.12.8+; `fresh-install.yml` on macOS |
| TD-MLX-IMPORT | `mlx` still imported when `engine=remote_asr` | RAM + slow start on edge Mac | Lazy-import in `transcription/engine.py` |
| TD-LAUNCHD | launchd lacks microphone | Broken autostart story | README: Login Items only; deprecate `--install` or warn |
| TD-LOCK | `clients/linux/uv.lock` + root `uv.lock` | Two dependency worlds | Workspace or explicit “Linux install from clients/linux” |

## Open — P2

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-WHISPER-CPP | whisper.cpp paths in base, rarely used | Noise in config | Move to `mac-*-local` only or optional profile |
| TD-TESTS-ENV | ENV override tests accept both outcomes | Weak contract | Assert ENV merge after profile load |
| TD-PYRIGHT | `clients/linux` not in pyright include | IDE noise | Extend include or mark optional |

## Architecture decisions (keep)

- **Two config schemas**: VTT2 `transcription.*` vs F9 `asr.*` — intentional.
- **No git merge** `main` ↔ `mlx-v1.1` — use copy + cherry-pick.
- **ASR server out of repo** — client-only; Enterprise Edge SKU.

## Review cadence

- Update this file on each release (2.0.x).
- Before cutover: all **P0/P1** either fixed or accepted with documented workaround.
