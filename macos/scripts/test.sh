#!/usr/bin/env bash
# Compile-and-run core tests with swiftc (SwiftPM is broken on some CLT installs).
# Every file in macos/VoiceToText/Tests is compiled into one binary; main.swift runs the suites.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/macos/VoiceToText"
# Same deployment target as build.sh, so tests see the same API availability.
TARGET="arm64-apple-macos13.0"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
OUT="$WORK/vtt-core-tests"

swiftc \
  -target "$TARGET" \
  -O \
  -o "$OUT" \
  "$PKG"/Sources/VoiceToTextCore/*.swift \
  "$PKG"/Tests/*.swift

# Run from the temp dir: tests write their own config files and logs there,
# never the repo config.yaml or ~/Library/Logs/vtt2.
(cd "$WORK" && VTT2_TEST_TMP="$WORK" "$OUT")
echo "swiftc tests OK"
