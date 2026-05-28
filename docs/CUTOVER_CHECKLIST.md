# Cutover checklist (phase A4)

Complete before making `product-unified` the default branch.

## Automated / local

- [x] `uv run pytest` — all green
- [x] `git grep -E '100\.\d+\.\d+\.\d+'` — no Tailscale IPs in tracked files (CI enforces)
- [ ] `vtt doctor --profile mac-m1-remote` — ASR ✅ when `.env.local` set (manual)
- [ ] `vtt mac run --profile mac-m4-local --health` — MLX import OK (`--extra local-mlx`)
- [x] `vtt validate-config` — all six profiles load
- [x] `vtt linux run --profile linux-f9-local --health` — config path (manual on Linux box)

## Manual smoke

- [ ] M1: record + transcribe with `mac-m1-remote`
- [ ] M4 (if available): local MLX with `mac-m4-local`
- [ ] Linux (if available): F9 hotkey with `linux-f9-local`

## Git / GitHub

- [ ] Tag `legacy/mlx-v1.1-2026-05` on current `mlx-v1.1` tip
- [ ] Tag `legacy/main-2026-05` on current `main` tip
- [ ] Set default branch to `product-unified`
- [x] Update README install links to `product-unified`
- [ ] Do **not** delete `mlx-v1.1` or `main`
- [ ] GitHub Release **v2.1.0** «Golden Standard»

## Documentation

- [x] [PRODUCT_MATRIX.md](PRODUCT_MATRIX.md) matches shipped profiles
- [x] [ENTERPRISE_EDGE.md](ENTERPRISE_EDGE.md) + [enterprise/INSTALL.md](enterprise/INSTALL.md)
- [x] [GOLDEN_STANDARD.md](GOLDEN_STANDARD.md)
- [x] [CHANGELOG.md](../CHANGELOG.md) entry for 2.1.0
