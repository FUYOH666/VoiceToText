#!/usr/bin/env bash
# VoiceToText — install or update in one command (Apple Silicon, macOS 13+).
#
#   curl -fsSL https://raw.githubusercontent.com/FUYOH666/VoiceToText/main/scripts/install.sh | bash
#
# Everything is built on this Mac from source: no Developer ID or notarization
# is needed, and Gatekeeper has nothing to block. Steps:
#   1. check the Mac (Apple Silicon, macOS 13+, Xcode Command Line Tools)
#   2. install uv if missing (Python and dependencies come through it)
#   3. download or update the source in ~/.voicetotext
#   4. Python environment
#   5. a local code-signing identity, so permissions survive updates
#   6. build VoiceToText.app
#   7. download the speech model recommended for this Mac's memory
#   8. start the two background services and add the app to ~/Applications
#
# Options (after `bash -s --` when piping):
#   --dir PATH      install location (default ~/.voicetotext)
#   --branch NAME   git branch (default main)
#   --model ID      speech model instead of the recommended one (see --list-models)
#   --no-model      skip the model download (it happens on the first dictation)
#   --no-services   build only; don't touch LaunchAgents
#   --force         replace an install that lives in another folder
#   --dry-run       print the steps without changing anything
set -euo pipefail

REPO_URL="${VTT_REPO_URL:-https://github.com/FUYOH666/VoiceToText.git}"
INSTALL_DIR="${VTT_HOME:-$HOME/.voicetotext}"
BRANCH="main"
MODEL=""
FETCH_MODEL=1
SERVICES=1
FORCE=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) INSTALL_DIR="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --no-model) FETCH_MODEL=0; shift ;;
    --no-services) SERVICES=0; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,25p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1;34m▸ %s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }
fail() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '  [dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

bold "VoiceToText installer"
note "Location: $INSTALL_DIR  (branch $BRANCH)"

# 1. The Mac -------------------------------------------------------------------
step "Checking this Mac"
[[ "$(uname -s)" == "Darwin" ]] || fail "VoiceToText runs on macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "Apple Silicon (M1 or newer) is required: the models run on MLX."
MACOS_MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
[[ "$MACOS_MAJOR" -ge 13 ]] || fail "macOS 13 Ventura or newer is required (found $(sw_vers -productVersion))."
MEMORY_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
note "macOS $(sw_vers -productVersion), $MEMORY_GB GB memory"

if ! xcode-select -p >/dev/null 2>&1 || ! command -v swiftc >/dev/null 2>&1; then
  note "Xcode Command Line Tools are needed to build the app (git, swiftc)."
  if [[ $DRY_RUN -eq 0 ]]; then
    xcode-select --install >/dev/null 2>&1 || true
  fi
  fail "A system window to install the Command Line Tools should be open now. Finish it, then run this installer again."
fi
note "Command Line Tools: $(xcode-select -p)"

# Refuse to silently take over an install that lives somewhere else.
EXISTING_PLIST="$HOME/Library/LaunchAgents/ai.vtt2.stt.plist"
if [[ -f "$EXISTING_PLIST" && $SERVICES -eq 1 ]]; then
  EXISTING_DIR="$(/usr/libexec/PlistBuddy -c 'Print :WorkingDirectory' "$EXISTING_PLIST" 2>/dev/null || true)"
  if [[ -n "$EXISTING_DIR" && "$EXISTING_DIR" != "$INSTALL_DIR" && $FORCE -eq 0 ]]; then
    fail "VoiceToText is already installed from $EXISTING_DIR. Update it there (git pull + --install), or re-run with --force to move it to $INSTALL_DIR."
  fi
fi

# 2. uv ------------------------------------------------------------------------
step "uv (Python toolchain)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
  note "uv $(uv --version | awk '{print $2}')"
else
  note "Installing uv from astral.sh (official installer)…"
  if [[ $DRY_RUN -eq 0 ]]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    note "[dry-run] curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi
fi

# 3. Source --------------------------------------------------------------------
step "Source code"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  note "Updating $INSTALL_DIR"
  run git -C "$INSTALL_DIR" fetch --quiet origin "$BRANCH"
  run git -C "$INSTALL_DIR" checkout --quiet "$BRANCH" \
    || fail "Could not switch $INSTALL_DIR to $BRANCH. Check: git -C \"$INSTALL_DIR\" status"
  run git -C "$INSTALL_DIR" merge --ff-only --quiet "origin/$BRANCH" \
    || fail "$INSTALL_DIR has local changes or a diverged history, so it can't be updated automatically. Check: git -C \"$INSTALL_DIR\" status (your settings live in ~/Library/Application Support/VoiceToText, not there)."
elif [[ -e "$INSTALL_DIR" && -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
  fail "$INSTALL_DIR exists and is not a VoiceToText checkout. Choose another folder with --dir."
else
  run git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi
[[ $DRY_RUN -eq 1 ]] || cd "$INSTALL_DIR"

# 4. Python environment ----------------------------------------------------------
step "Python environment (first run downloads Python 3.12 and MLX, ~1 GB)"
run uv sync --frozen --extra qwen

# 5. Signing ---------------------------------------------------------------------
step "Local code-signing identity"
if security find-identity -v -p codesigning 2>/dev/null | grep -F '"vtt-local-codesign"' >/dev/null; then
  note "Already present."
else
  note "Creating it once. macOS may ask for your password to trust it."
  if [[ $DRY_RUN -eq 1 ]]; then
    note "[dry-run] bash macos/scripts/setup-local-signing.sh"
  elif ! bash macos/scripts/setup-local-signing.sh; then
    note "Skipped: the app will be signed ad-hoc, and macOS will ask for permissions again after each update."
  fi
fi

# 6. App -----------------------------------------------------------------------
step "Building VoiceToText.app"
run bash macos/scripts/build.sh

# 7. Model ---------------------------------------------------------------------
if [[ $FETCH_MODEL -eq 1 ]]; then
  step "Speech model"
  if [[ -n "$MODEL" ]]; then
    run uv run --frozen python scripts/prefetch_model.py --model "$MODEL"
  else
    run uv run --frozen python scripts/prefetch_model.py
  fi
else
  note "Model download skipped; the first dictation will fetch it."
fi

# 8. Services --------------------------------------------------------------------
if [[ $SERVICES -eq 1 ]]; then
  step "Background services (start at login)"
  run uv run --frozen python src/vtt2/main.py --install
  mkdir -p "$HOME/Applications"
  run ln -sfn "$INSTALL_DIR/macos/dist/VoiceToText.app" "$HOME/Applications/VoiceToText.app"
  if [[ $DRY_RUN -eq 0 ]]; then
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" || true
  fi
else
  note "Services not installed (--no-services)."
fi

if [[ $SERVICES -eq 0 ]]; then
  bold ""
  bold "✓ VoiceToText is built in $INSTALL_DIR (services not installed)."
  note "Start it with: cd \"$INSTALL_DIR\" && uv run python src/vtt2/main.py --install"
  exit 0
fi

bold ""
bold "✓ VoiceToText is installed."
cat <<EOF

  Two permissions, once:
    • Microphone — allow when macOS asks.
    • Accessibility — System Settings → Privacy & Security → Accessibility → turn on VoiceToText
      (the window is open now; if VoiceToText is not listed, add ~/Applications/VoiceToText.app).

  Use it: hold Option+Space, speak, let go — the text appears where your cursor is.
          Tap Option+Space to start and again to stop. Esc cancels.
  Menu bar: model choice, history, glossary of your terms.

  Update later: run the same command again.
  Remove:       bash "$INSTALL_DIR/scripts/uninstall.sh"
EOF
