# Golden Standard — VoiceToText

This document is the **constitution** for the `product-unified` branch. When in doubt, follow this file.

## Product identity

- **Name:** VoiceToText (VTT)
- **Version:** single semver in `pyproject.toml`, synced to `config/base.yaml` via `scripts/sync_version.py`
- **SKU model:** hardware profiles in `config/profiles/`, not hand-edited monolithic YAML

## The six profiles (only supported configurations)

| Profile | Platform | Inference |
|---------|----------|-----------|
| `mac-m1-local` | macOS | MLX on Mac |
| `mac-m1-remote` | macOS | Private ASR server |
| `mac-m4-local` | macOS | MLX on Mac |
| `mac-m4-remote` | macOS | Private ASR server |
| `linux-f9-local` | Linux | ASR on localhost |
| `linux-f9-edge` | Linux | ASR on Tailnet host |

Active profile: `config.yaml` → `active_profile`, or `VTT2_PROFILE` / `--profile`.

## Secrets

- **Never** commit Tailscale IPs, tokens, or `/Users/...` paths.
- ASR URL: `LOCAL_AI_ASR_BASE_URL` in **`.env.local`** (gitignored).
- Template: `.env.example`, service template: `.env.vtt2.example`.

## Commands (one CLI)

```bash
uv sync --extra mac        # Mac menu-bar client
uv sync --extra mac --extra local-mlx  # Mac + offline MLX
uv sync                    # Linux F9 / CI core only

vtt profiles list
vtt validate-config
vtt doctor
vtt mac run --profile mac-m1-remote
vtt linux run --profile linux-f9-local --health
```

## Forbidden

- `git merge` between `main` and `mlx-v1.1` (unrelated histories)
- Putting ASR GPU server code in this repo (client-only)
- Public cloud STT as default
- New config files with real hostnames in git

## Definition of Done (every PR)

- [ ] `uv run pytest` passes
- [ ] `vtt validate-config` passes
- [ ] No new secrets in `git diff`
- [ ] README / CHANGELOG updated if behavior or UX changed
- [ ] Profiles remain the only way to change engine/hardware defaults

## 10/10 scorecard

See [CUTOVER_CHECKLIST.md](CUTOVER_CHECKLIST.md). All items must be checked before default branch cutover.

## Legacy branches

`mlx-v1.1` and `main` are tagged `legacy/*` and frozen for reference. Development happens on **`product-unified`** only.
