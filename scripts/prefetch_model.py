#!/usr/bin/env python3
"""Download the model recommended for this Mac (or --model ID) and select it.

Used by scripts/install.sh so the first dictation doesn't wait for a
multi-GB download inside the request. Run in the project env:

    uv run python scripts/prefetch_model.py              # recommended for this Mac
    uv run python scripts/prefetch_model.py --list       # show the catalog
    uv run python scripts/prefetch_model.py --model whisper-large-v3-turbo-8bit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "vtt2"))

from model_catalog.registry import (  # noqa: E402
    ALLOW_PATTERNS,
    is_installed,
    load_catalog,
    system_memory_gb,
    write_selection,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", help="catalog id (default: recommended for this Mac's memory)")
    parser.add_argument("--list", action="store_true", help="print the catalog and exit")
    parser.add_argument("--no-select", action="store_true", help="download only, keep the current model")
    args = parser.parse_args()

    catalog = load_catalog()
    memory = system_memory_gb()
    recommended = catalog.recommended(memory)

    if args.list:
        print(f"Mac memory: {memory:.0f} GB")
        for m in catalog.models:
            flags = []
            if m.id == recommended:
                flags.append("recommended")
            if memory and memory < m.min_memory_gb:
                flags.append(f"needs {m.min_memory_gb:.0f} GB")
            if is_installed(m):
                flags.append("downloaded")
            print(f"  {m.id:30s} {m.download_gb:5.2f} GB  {m.title}  {' · '.join(flags)}")
        return 0

    model_id = args.model or recommended
    spec = catalog.get(model_id) if model_id else None
    if spec is None:
        print(f"Unknown model: {model_id}. Use --list.", file=sys.stderr)
        return 2
    if memory and memory < spec.min_memory_gb:
        print(f"Warning: {spec.title} wants {spec.min_memory_gb:.0f} GB, this Mac has {memory:.0f} GB.")

    print(f"Model: {spec.title} — {spec.download_gb:.2f} GB download, ~{spec.ram_gb:.1f} GB in memory")
    if is_installed(spec):
        print("Already downloaded.")
    else:
        from huggingface_hub import snapshot_download

        snapshot_download(repo_id=spec.repo, allow_patterns=ALLOW_PATTERNS[spec.family])
        if not is_installed(spec):
            print("Download finished but the weights are missing.", file=sys.stderr)
            return 1
        print("Downloaded.")

    if not args.no_select:
        path = write_selection(spec)
        print(f"Selected as the active model ({path}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
