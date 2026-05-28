## 2.1.1 — M1 local default, F9 env fix, GitHub polish

### Fixes
- F9: `.env.local` no longer overrides `linux-f9-local` ASR URL (only `linux-f9-edge`)

### Changes
- Default profile: `mac-m1-local` (local MLX on M1)
- Startup logs show profile, engine, and model
- CONTRIBUTING, SECURITY, issue templates, TROUBLESHOOTING, README.ru

### Upgrade
```bash
git pull origin product-unified
uv sync --extra mac --extra local-mlx
./.venv/bin/python src/vtt2/main.py --profile mac-m1-local
```
