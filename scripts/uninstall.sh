#!/usr/bin/env bash
# Remove VoiceToText's background services and app link.
#
#   bash ~/.voicetotext/scripts/uninstall.sh            # services + app link
#   bash ~/.voicetotext/scripts/uninstall.sh --purge    # also source, history, settings
#
# Downloaded speech models stay in the Hugging Face cache (~/.cache/huggingface);
# delete them from the app's model menu before uninstalling, or remove that
# cache yourself if nothing else uses it.
set -euo pipefail

PURGE=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    --force) FORCE=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
UID_NUM="$(id -u)"

# Only touch services that belong to *this* copy (their WorkingDirectory is
# ROOT), so running another checkout's uninstall.sh can't take down this one.
for label in ai.vtt2 ai.vtt2.stt; do
  plist="$HOME/Library/LaunchAgents/$label.plist"
  [[ -f "$plist" ]] || continue
  owner="$(/usr/libexec/PlistBuddy -c 'Print :WorkingDirectory' "$plist" 2>/dev/null || true)"
  owner_real="$(cd "$owner" 2>/dev/null && pwd -P || echo "$owner")"
  if [[ "$owner_real" != "$ROOT" && $FORCE -eq 0 ]]; then
    echo "Skipped $label: it belongs to ${owner:-another install} (use --force to remove anyway)"
    continue
  fi
  launchctl bootout "gui/$UID_NUM" "$plist" 2>/dev/null || launchctl unload "$plist" 2>/dev/null || true
  rm -f "$plist"
  echo "Removed service $label"
done

link="$HOME/Applications/VoiceToText.app"
if [[ -L "$link" ]]; then
  target="$(readlink "$link")"
  if [[ "$target" == "$ROOT"/* || $FORCE -eq 1 ]]; then
    rm -f "$link"
    echo "Removed ~/Applications/VoiceToText.app link"
  fi
fi

if [[ $PURGE -eq 1 ]]; then
  rm -rf "$HOME/Library/Application Support/VoiceToText"
  echo "Removed history, recordings and settings"
  if [[ -d "$ROOT/.git" && "$ROOT" == "$HOME/.voicetotext" ]]; then
    rm -rf "$ROOT"
    echo "Removed $ROOT"
  else
    echo "Source left in place: $ROOT"
  fi
fi

echo "VoiceToText is uninstalled. Remove it from System Settings → Privacy & Security → Accessibility if you like."
