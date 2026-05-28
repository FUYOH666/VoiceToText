# Cutover checklist (phase A4)

Complete before making `product-unified` the default branch.

## Automated / local

- [ ] `uv run pytest` — all green
- [ ] `git grep -E '100\.\d+\.\d+\.\d+'` — no Tailscale IPs in tracked files
- [ ] `uv run python src/vtt2/main.py --profile mac-m1-remote --health` — config ✅ (remote ASR ✅ when `.env.local` set)
- [ ] `uv run python src/vtt2/main.py --profile mac-m4-local --health` — MLX import OK (with `--extra local-mlx`)
- [ ] `VTT2_PROFILE=linux-f9-local` — F9 config loads (`python -c` from [clients/linux/README.md](../clients/linux/README.md))

## Manual smoke

- [ ] M1: record + transcribe with `mac-m1-remote`
- [ ] M4 (if available): local MLX with `mac-m4-local`
- [ ] Linux (if available): F9 hotkey with `linux-f9-local`

## Git / GitHub

- [ ] Tag `legacy/mlx-v1.1-YYYY-MM` on current `mlx-v1.1` tip
- [ ] Tag `legacy/main-YYYY-MM` on current `main` tip
- [ ] Set default branch to `product-unified`
- [ ] Update README install links to `product-unified`
- [ ] Do **not** delete `mlx-v1.1` or `main`

## Documentation

- [ ] [PRODUCT_MATRIX.md](PRODUCT_MATRIX.md) matches shipped profiles
- [ ] [ENTERPRISE_EDGE.md](ENTERPRISE_EDGE.md) reviewed for customer-facing copy
- [ ] [CHANGELOG.md](../CHANGELOG.md) entry for 2.0.0
