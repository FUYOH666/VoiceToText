## Summary

<!-- What changed and why -->

## Test plan

- [ ] `uv run pytest`
- [ ] `vtt validate-config` (if config/CLI touched)
- [ ] No secrets in diff (no `.env.local`, no Tailscale IPs)

## Checklist

- [ ] [CHANGELOG.md](../CHANGELOG.md) updated (user-visible changes)
- [ ] Profiles remain the only way to change engine defaults (no new secret YAML hosts)
