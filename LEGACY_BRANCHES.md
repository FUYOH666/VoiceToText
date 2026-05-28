# Legacy branches

VoiceToText uses **three git lines** until `product-unified` passes the cutover checklist.

| Branch | Role | Daily use |
|--------|------|-----------|
| `mlx-v1.1` | Production Mac client (pre-unified config) | Stable fallback |
| `main` | Linux F9 client + old macOS/MLX monorepo (`platforms/*`) | Source for `clients/linux` copy only |
| `product-unified` | **Active development** — profiles, shared ASR client, docs | New features and config |

## Git history

`main` and `mlx-v1.1` have **no common ancestor**. Do not `git merge` them. Copy files or cherry-pick commits instead.

## Cherry-pick policy

1. Bugfixes land on the branch where the bug was found.
2. If the fix applies to `product-unified`, cherry-pick into `product-unified`.
3. Hotfixes for users still on `mlx-v1.1` may be cherry-picked back from `product-unified` when low-risk.
4. Do not backport profile-based config to `mlx-v1.1` except emergency hotfixes.

## Cutover (phase A4)

When [docs/CUTOVER_CHECKLIST.md](docs/CUTOVER_CHECKLIST.md) is complete:

1. Tag `legacy/mlx-v1.1-YYYY-MM` and `legacy/main-YYYY-MM` on current tips.
2. Set GitHub **default branch** to `product-unified`.
3. Keep legacy branches; do not delete.
