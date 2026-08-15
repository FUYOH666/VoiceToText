#!/usr/bin/env bash
# Developer ID sign + notarytool + staple. Requires macos/Signing.xcconfig or env.
# Artifacts: macos/dist/VoiceToText.app and macos/dist/VoiceToText.app.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/macos/dist/VoiceToText.app"
ZIP="$ROOT/macos/dist/VoiceToText.app.zip"
ENTITLEMENTS="$ROOT/macos/VoiceToText/Resources/VoiceToText.entitlements"
SIGNING="$ROOT/macos/Signing.xcconfig"

DEVELOPMENT_TEAM="${VTT2_DEVELOPMENT_TEAM:-}"
CODE_SIGN_IDENTITY="${VTT2_CODE_SIGN_IDENTITY:-}"
NOTARY_PROFILE="${VTT2_NOTARY_PROFILE:-}"

if [[ -f "$SIGNING" ]]; then
  # shellcheck disable=SC1090
  DEVELOPMENT_TEAM="${DEVELOPMENT_TEAM:-$(awk -F' = ' '/^DEVELOPMENT_TEAM/{print $2}' "$SIGNING")}"
  CODE_SIGN_IDENTITY="${CODE_SIGN_IDENTITY:-$(awk -F' = ' '/^CODE_SIGN_IDENTITY/{print $2}' "$SIGNING")}"
  NOTARY_PROFILE="${NOTARY_PROFILE:-$(awk -F' = ' '/^NOTARY_PROFILE/{print $2}' "$SIGNING")}"
fi

if [[ -z "$DEVELOPMENT_TEAM" || "$DEVELOPMENT_TEAM" == "YOUR_TEAM_ID" || -z "$CODE_SIGN_IDENTITY" ]]; then
  echo "Missing Developer ID. Copy macos/Signing.xcconfig.example → macos/Signing.xcconfig" >&2
  echo "or set VTT2_DEVELOPMENT_TEAM and VTT2_CODE_SIGN_IDENTITY." >&2
  exit 2
fi

bash "$ROOT/macos/scripts/build.sh"

echo "Signing with $CODE_SIGN_IDENTITY (team $DEVELOPMENT_TEAM)"
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" \
  --sign "$CODE_SIGN_IDENTITY" \
  "$APP"

codesign --verify --deep --strict --verbose=2 "$APP"

rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"

if [[ -z "$NOTARY_PROFILE" || "$NOTARY_PROFILE" == "VTT2_NOTARY" ]]; then
  if [[ -z "${VTT2_NOTARY_PROFILE:-}" ]]; then
    echo "No notary profile. Create one:" >&2
    echo "  xcrun notarytool store-credentials VTT2_NOTARY --apple-id ... --team-id $DEVELOPMENT_TEAM" >&2
    echo "Zip ready (unsigned-notary): $ZIP" >&2
    exit 3
  fi
fi

xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$APP"
spctl --assess --type execute --verbose "$APP" || true

rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"
echo "Notarized: $ZIP"
