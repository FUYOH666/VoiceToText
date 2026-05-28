# Contributing to VoiceToText

Thank you for helping make private, local voice-to-text accessible to everyone.

## Development setup

```bash
git clone https://github.com/FUYOH666/VoiceToText.git
cd VoiceToText
git checkout product-unified
uv sync --extra dev --extra mac --extra local-mlx
uv run pytest
```

Mac menu-bar only: `uv sync --extra dev --extra mac --extra local-mlx`  
Linux F9 client only: `uv sync --extra dev`

## Branch

- Default: **`product-unified`**
- Do not merge `main` and `mlx-v1.1` (unrelated histories). See [LEGACY_BRANCHES.md](LEGACY_BRANCHES.md).

## Configuration

- Use profiles in `config/profiles/` — do not add secrets to YAML.
- Secrets: `.env.local` only (see `.env.example`). **Never commit** IPs, tokens, or `/Users/...` paths.

## Pull requests

1. `uv run pytest` passes
2. `vtt validate-config` passes (after `uv pip install -e .`)
3. No secrets in `git diff`
4. Update [CHANGELOG.md](CHANGELOG.md) for user-visible changes
5. Use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)

## Code style

- Python 3.12+, `uv` for dependencies
- `logging`, not `print`, in application code
- Match existing patterns in `src/vtt2` and `src/vtt_asr_client`

## Security

See [SECURITY.md](SECURITY.md).
