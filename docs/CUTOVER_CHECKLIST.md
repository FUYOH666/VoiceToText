# Cutover checklist

**Status:** cutover completed on `product-unified` (default branch, v2.1.0+).

## Automated / local

- [x] `uv run pytest` — all green (CI on push)
- [x] No Tailscale IPs in tracked config (CI grep)
- [x] `vtt validate-config` — six profiles
- [ ] `vtt doctor --profile mac-m1-remote` — when ASR server online

## Manual smoke (your machine)

- [ ] **M1 local:** `./.venv/bin/python src/vtt2/main.py --profile mac-m1-local` → Option+Space → text pasted; log shows `mlx_engine`, not `remote_asr_engine`
- [ ] M4 local MLX (if available)
- [ ] Linux F9 hotkey (if available)

## Git / GitHub

- [x] Tags `legacy/mlx-v1.1-2026-05`, `legacy/main-2026-05`
- [x] Default branch `product-unified`
- [x] Release v2.1.0 Golden Standard
- [x] Release v2.1.1 (ship pass)
- [x] Legacy branches not deleted

## Documentation

- [x] PRODUCT_MATRIX, ENTERPRISE_EDGE, GOLDEN_STANDARD
- [x] CHANGELOG 2.1.x
- [x] TROUBLESHOOTING, CONTRIBUTING, SECURITY
