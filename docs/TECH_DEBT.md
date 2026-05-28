# Technical debt register — product-unified

Living document. Severity: **P0** (blocker), **P1** (soon), **P2** (nice).

## Resolved in 2.0.0

| ID | Was | Fix |
|----|-----|-----|
| TD-CONFIG | Single `config.yaml` drift M1/M4/remote | `config/base.yaml` + `config/profiles/*` |
| TD-SECRET | Tailscale IP in tracked YAML | `.env.local` + placeholder only |
| TD-DUP-ASR | Duplicate HTTP client Mac/Linux | `src/vtt_asr_client` |
| TD-BRANCH | No sandbox for unified product | `product-unified` branch |

## Open — P1

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-UV-RUMPS | `uv sync` may fail building `rumps` (packaging 26) | Fresh install breaks | Document `uv sync --extra local-mlx`; pin Python 3.12.x final; CI smoke |
| TD-MLX-IMPORT | `mlx` still imported when `engine=remote_asr` | RAM + slow start on edge Mac | Lazy-import in `transcription/engine.py` |
| TD-F9-CONFIG | F9 still has `clients/linux/config.yaml` separate from profiles | Two sources of truth | Wire `F9Config.from_profile()` in F9 `main.py` (Phase 2) |
| TD-LAUNCHD | launchd lacks microphone | Broken autostart story | README: Login Items only; deprecate `--install` or warn |
| TD-LOCK | `clients/linux/uv.lock` + root `uv.lock` | Two dependency worlds | Workspace or explicit “Linux install from clients/linux” |
| TD-VERSION | `app.version` in yaml vs `pyproject.toml` | Confusion | Single bump script or generate from pyproject |

## Open — P2

| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| TD-ARTIFACTS | `strip_whisper_tail_artifacts` not in pydantic/text path | Quality vs mlx-v1.1 README | Port from mlx-v1.1 if present |
| TD-WHISPER-CPP | whisper.cpp paths in base, rarely used | Noise in config | Move to `mac-*-local` only or optional profile |
| TD-CI | No GitHub Actions | Regressions | pytest + `git grep` for IPs |
| TD-TESTS-ENV | ENV override tests accept both outcomes | Weak contract | Assert ENV merge after profile load |
| TD-PYRIGHT | `clients/linux` not in pyright include | IDE noise | Extend include or mark optional |

## Architecture decisions (keep)

- **Two config schemas**: VTT2 `transcription.*` vs F9 `asr.*` — intentional.
- **No git merge** `main` ↔ `mlx-v1.1` — use copy + cherry-pick.
- **ASR server out of repo** — client-only; Enterprise Edge SKU.

## Review cadence

- Update this file on each release (2.0.x).
- Before cutover: all **P0/P1** either fixed or accepted with documented workaround.
