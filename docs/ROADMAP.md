# Roadmap — VoiceToText product-unified

## Done (2.0.0 sandbox)

- [x] Branch `product-unified` with profile-based config (Mac + Linux F9 profiles)
- [x] Shared `vtt_asr_client` for remote ASR
- [x] Secrets out of git (`.env.local` + `.env.example`)
- [x] Docs: PRODUCT_MATRIX, ENTERPRISE_EDGE, CUTOVER_CHECKLIST, LEGACY_BRANCHES

## Phase 1 — Stabilize Mac (1–2 weeks)

| Item | Why | Done when |
|------|-----|-----------|
| Push + default smoke on M1 `mac-m1-remote` | Real-world validation | Health + one recording |
| `.env.vtt2.example` aligned with profiles | Login Items / launchd | Documented in README |
| Fix `uv sync` on fresh clone (rumps/packaging) | Reproducible install | CI or README workaround verified |
| Optional MLX: lazy import | Edge Mac never loads mlx | `engine=remote_asr` starts without mlx import |
| Whisper tail artifact stripping in VTT2 | Parity with mlx-v1.1 marketing | Config flag wired in text pipeline |

## Phase 2 — Linux product (2–3 weeks)

| Item | Why | Done when |
|------|-----|-----------|
| F9 uses `F9Config.from_profile()` in `main.py` | Single config source | No local `clients/linux/config.yaml` drift |
| Root `uv` workspace or documented dual install | One lockfile story | `uv sync` from repo root for F9 |
| F9 health CLI | Ops | `f9-asr --health` checks ASR |
| Integrate F9 into PRODUCT_MATRIX CI | Regression | pytest + smoke job |

## Phase 3 — Enterprise kit (3–4 weeks)

| Item | Why | Done when |
|------|-----|-----------|
| Install guide PDF/Markdown bundle | B2B sales | Tailscale + ASR + Mac profile |
| OpenAPI snippet for ASR contract | Client/server boundary | `docs/asr-api.md` |
| Profile validator CLI | Onboarding | `uv run python -m vtt2.config validate` |
| Telemetry-off audit log (local only) | Compliance narrative | Optional file log of request metadata |

## Phase 4 — Cutover (after matrix green)

See [CUTOVER_CHECKLIST.md](CUTOVER_CHECKLIST.md):

- Tags `legacy/mlx-v1.1-*`, `legacy/main-*`
- GitHub default branch → `product-unified`
- Archive notice on old branches

## Phase 5 — Monorepo polish (optional)

| Item | Why |
|------|-----|
| `apps/macos-vtt2`, `apps/linux-f9`, `packages/*` | Variant C from architecture audit |
| GitHub Actions: pytest, no IP grep, profile matrix | CI gate |
| Single semver release (GitHub Release) | Product versioning |

## Non-goals (for now)

- Merging `main` and `mlx-v1.1` git histories
- Embedding ASR server into this repo (stays separate GPU deploy)
- Public SaaS / cloud STT integration
