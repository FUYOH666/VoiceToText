## Summary

<!-- What changed and why -->

## Test plan

- [ ] `uv run pytest -q`
- [ ] `macos/scripts/test.sh` and `macos/scripts/build.sh` (if `macos/` touched)
- [ ] `uv run python scripts/sync_version.py --check` (if a version changed, edit only `pyproject.toml` and run the script without `--check`)
- [ ] No secrets or personal paths in the diff (`.env*`, tokens, private IPs, `/Users/<name>/`)

## Checklist

- [ ] [CHANGELOG.md](../CHANGELOG.md) updated for user-visible changes
- [ ] [docs/STT_API.md](../docs/STT_API.md) updated if the HTTP API changed
