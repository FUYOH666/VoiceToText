#!/usr/bin/env bash
# Build VoiceToText.app (LSUIElement) via SwiftPM. No Xcode.app required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/macos/VoiceToText"
DIST="$ROOT/macos/dist/VoiceToText.app"
BIN_NAME="VoiceToText"

STAGE="$(mktemp -d)"
BIN="$STAGE/$BIN_NAME"

# SwiftPM PackageDescription is broken on some Command Line Tools; swiftc is the source of truth.
swiftc -parse-as-library \
  -O \
  -o "$BIN" \
  "$PKG/Sources/VoiceToTextCore/AppLog.swift" \
  "$PKG/Sources/VoiceToTextCore/AppConfig.swift" \
  "$PKG/Sources/VoiceToTextCore/STTClient.swift" \
  "$PKG/Sources/VoiceToTextCore/WAVEncoder.swift" \
  "$PKG/Sources/VoiceToText/HotkeyController.swift" \
  "$PKG/Sources/VoiceToText/Recorder.swift" \
  "$PKG/Sources/VoiceToText/Paster.swift" \
  "$PKG/Sources/VoiceToText/AppState.swift" \
  "$PKG/Sources/VoiceToText/App.swift" \
  -framework SwiftUI \
  -framework AppKit \
  -framework AVFoundation \
  -framework Carbon \
  -framework CoreGraphics \
  -framework ApplicationServices

rm -rf "$DIST"
mkdir -p "$DIST/Contents/MacOS" "$DIST/Contents/Resources"
cp "$BIN" "$DIST/Contents/MacOS/$BIN_NAME"
cp "$PKG/Resources/Info.plist" "$DIST/Contents/Info.plist"
cp "$PKG/Resources/VoiceToText.entitlements" "$DIST/Contents/Resources/VoiceToText.entitlements"
if [[ -f "$PKG/Resources/icon.png" ]]; then
  cp "$PKG/Resources/icon.png" "$DIST/Contents/Resources/icon.png"
fi

# Ad-hoc sign for local daily driver (no hardened runtime — that is release.sh).
if command -v codesign >/dev/null; then
  codesign --force --sign - --entitlements "$PKG/Resources/VoiceToText.entitlements" "$DIST" \
    || true
fi

echo "Built $DIST"
