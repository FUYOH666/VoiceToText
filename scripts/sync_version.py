#!/usr/bin/env python3
"""Propagate the version in pyproject.toml (single source of truth) to every other copy.

Targets:
  - macos/VoiceToText/Resources/Info.plist: CFBundleShortVersionString and CFBundleVersion
  - config*.yaml in the repo root (except config.local.yaml): app.version
  - src/vtt2/__init__.py: __version__

Usage:
  python scripts/sync_version.py          # rewrite targets to match pyproject.toml
  python scripts/sync_version.py --check  # exit 1 if any target is out of date (CI)

Stdlib only, so it runs before `uv sync`.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INFO_PLIST = ROOT / "macos" / "VoiceToText" / "Resources" / "Info.plist"
INIT_PY = ROOT / "src" / "vtt2" / "__init__.py"
LOCAL_CONFIG = "config.local.yaml"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
PLIST_KEYS = ("CFBundleShortVersionString", "CFBundleVersion")


class SyncError(Exception):
    pass


def read_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not SEMVER.match(version):
        # CFBundleShortVersionString and CFBundleVersion accept only dotted integers.
        raise SyncError(f"pyproject.toml [project].version must be X.Y.Z, got {version!r}")
    return version


def sync_plist(text: str, version: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for key in PLIST_KEYS:
        pattern = re.compile(rf"(<key>{key}</key>\s*<string>)([^<]*)(</string>)")
        match = pattern.search(text)
        if match is None:
            raise SyncError(f"{key} not found")
        found.append(f"{key}={match.group(2)}")
        text = pattern.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", text, count=1)
    return text, found


def sync_config_yaml(text: str, version: str) -> tuple[str, list[str]]:
    """Rewrite `version:` inside the top-level `app:` mapping; leave every other line alone."""
    lines = text.splitlines(keepends=True)
    in_app = False
    child_indent: str | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            in_app = re.match(r"^app:\s*(#.*)?$", line.rstrip("\r\n")) is not None
            child_indent = None
            continue
        if not in_app:
            continue
        indent = line[: len(line) - len(line.lstrip())]
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue  # nested deeper than app's own keys
        match = re.match(r"^(\s+version:\s*)([\"']?)([^\"'#\s]*)\2(.*)$", line.rstrip("\r\n"))
        if match is None:
            continue
        indent_key, quote, old, rest = match.groups()
        newline = line[len(line.rstrip("\r\n")) :]
        quote = quote or '"'
        lines[i] = f"{indent_key}{quote}{version}{quote}{rest}{newline}"
        return "".join(lines), [f"app.version={old}"]
    raise SyncError("app.version not found")


def sync_init(text: str, version: str) -> tuple[str, list[str]]:
    pattern = re.compile(r"^(__version__\s*=\s*)([\"'])([^\"']*)\2", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        raise SyncError("__version__ not found")
    new = pattern.sub(lambda m: f'{m.group(1)}"{version}"', text, count=1)
    return new, [f"__version__={match.group(3)}"]


def targets() -> list[tuple[Path, Callable[[str, str], tuple[str, list[str]]]]]:
    configs = sorted(p for p in ROOT.glob("config*.yaml") if p.name != LOCAL_CONFIG)
    if not configs:
        raise SyncError("no config*.yaml found in repo root")
    return [
        (INFO_PLIST, sync_plist),
        *((path, sync_config_yaml) for path in configs),
        (INIT_PY, sync_init),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if any target differs from pyproject.toml",
    )
    args = parser.parse_args(argv)

    try:
        version = read_version()
        stale: list[str] = []
        for path, sync in targets():
            rel = path.relative_to(ROOT)
            original = path.read_text(encoding="utf-8")
            try:
                updated, old = sync(original, version)
            except SyncError as exc:
                raise SyncError(f"{rel}: {exc}") from None
            if updated == original:
                continue
            stale.append(f"{rel} ({', '.join(old)})")
            if not args.check:
                path.write_text(updated, encoding="utf-8")
    except (OSError, SyncError, tomllib.TOMLDecodeError) as exc:
        print(f"sync_version: {exc}", file=sys.stderr)
        return 2

    if not stale:
        print(f"All versions match pyproject.toml: {version}")
        return 0
    if args.check:
        print(f"Out of sync with pyproject.toml ({version}):", file=sys.stderr)
        for item in stale:
            print(f"  {item}", file=sys.stderr)
        print("Run: uv run python scripts/sync_version.py", file=sys.stderr)
        return 1
    print(f"Synced version {version}:")
    for item in stale:
        print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
