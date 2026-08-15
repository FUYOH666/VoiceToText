#!/usr/bin/env bash
# Compile-and-run core tests with swiftc (SwiftPM is broken on some CLT installs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/macos/VoiceToText"
OUT="$(mktemp -d)/vtt-core-tests"

swiftc \
  -O \
  -o "$OUT" \
  "$PKG/Sources/VoiceToTextCore/AppLog.swift" \
  "$PKG/Sources/VoiceToTextCore/AppConfig.swift" \
  "$PKG/Sources/VoiceToTextCore/STTClient.swift" \
  "$PKG/Sources/VoiceToTextCore/WAVEncoder.swift" \
  "$PKG/Tests/VoiceToTextCoreTests/MockURLProtocol.swift" \
  "$PKG/Tests/main.swift"

"$OUT"
echo "swiftc tests OK"
