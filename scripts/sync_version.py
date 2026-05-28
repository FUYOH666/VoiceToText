#!/usr/bin/env python3
"""Sync version from pyproject.toml to config/base.yaml (single source of truth)."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    base_yaml = root / "config" / "base.yaml"

    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        print("Could not find version in pyproject.toml", file=sys.stderr)
        return 1

    version = match.group(1)
    content = base_yaml.read_text(encoding="utf-8")
    updated, n = re.subn(
        r'(^\s+version:\s*")[^"]+(")',
        rf'\g<1>{version}\2',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        print("Could not update app.version in config/base.yaml", file=sys.stderr)
        return 1

    base_yaml.write_text(updated, encoding="utf-8")
    print(f"Synced version {version} -> config/base.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
