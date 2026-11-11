"""Resolve Hugging Face repo ids to already-downloaded local snapshots.

mlx-whisper and mlx-qwen3-asr call ``snapshot_download(repo_id)`` on every
model load. Even when the weights are cached, that is a network round trip to
huggingface.co on each reload after idle unload: slower on a bad network and
at odds with "no cloud". Passing the local snapshot directory instead makes
both libraries load straight from disk.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_cached_snapshot(repo_or_path: str) -> str:
    """Local snapshot dir for a cached repo id, else the input unchanged.

    Never touches the network. A local path, an unknown repo or a repo that
    was never downloaded is returned as is, so the caller's library downloads
    it the usual way.
    """
    if not repo_or_path or Path(repo_or_path).expanduser().exists():
        return repo_or_path
    try:
        from huggingface_hub import snapshot_download

        local = snapshot_download(repo_id=repo_or_path, local_files_only=True)
    except Exception as exc:  # not cached, invalid id, hub not installed
        logger.debug("No local snapshot for %s: %s", repo_or_path, exc)
        return repo_or_path
    if not (Path(local) / "config.json").is_file():
        return repo_or_path
    return str(local)
