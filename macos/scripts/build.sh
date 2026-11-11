#!/usr/bin/env bash
# Build VoiceToText.app (LSUIElement) with plain swiftc. No Xcode.app required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/macos/VoiceToText"
DIST="$ROOT/macos/dist/VoiceToText.app"
BIN_NAME="VoiceToText"
# Keep in sync with LSMinimumSystemVersion in Resources/Info.plist. Without an
# explicit target swiftc stamps the host OS as minos and older macOS refuses to launch.
TARGET="arm64-apple-macos13.0"

STAGE="$(mktemp -d)"
BIN="$STAGE/$BIN_NAME"

# SwiftPM PackageDescription is broken on some Command Line Tools; swiftc is the source of truth.
swiftc -parse-as-library \
  -target "$TARGET" \
  -O \
  -o "$BIN" \
  "$PKG/Sources/VoiceToTextCore/AppLog.swift" \
  "$PKG/Sources/VoiceToTextCore/AppConfig.swift" \
  "$PKG/Sources/VoiceToTextCore/ModelsClient.swift" \
  "$PKG/Sources/VoiceToTextCore/Glossary.swift" \
  "$PKG/Sources/VoiceToTextCore/STTClient.swift" \
  "$PKG/Sources/VoiceToTextCore/WAVEncoder.swift" \
  "$PKG/Sources/VoiceToTextCore/DictationStore.swift" \
  "$PKG/Sources/VoiceToTextCore/ClipboardSnapshot.swift" \
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

# Stable local identity keeps the designated requirement across rebuilds, so
# Microphone and Accessibility grants survive. Ad-hoc (`-`) changes cdhash every
# build and macOS drops those grants. No hardened runtime here — that is release.sh.
LOCAL_SIGN_IDENTITY="${VTT2_LOCAL_SIGN_IDENTITY:-vtt-local-codesign}"
SIGN_ID="-"
if security find-identity -v -p codesigning 2>/dev/null | grep -F "\"${LOCAL_SIGN_IDENTITY}\"" >/dev/null; then
  SIGN_ID="$LOCAL_SIGN_IDENTITY"
else
  echo "No stable identity '${LOCAL_SIGN_IDENTITY}'. Signing ad-hoc; paste permission resets on every rebuild." >&2
  echo "Run once: macos/scripts/setup-local-signing.sh" >&2
fi
codesign --force --sign "$SIGN_ID" --entitlements "$PKG/Resources/VoiceToText.entitlements" "$DIST"
codesign --verify --verbose=2 "$DIST"

echo "Built $DIST"
