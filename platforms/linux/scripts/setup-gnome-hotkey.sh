#!/bin/bash

# Setup GNOME hotkey for F9 ASR
# Настройка горячей клавиши GNOME для F9 ASR

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This script is designed for Linux systems only"
    exit 1
fi

# Check if GNOME is running
if [ "$XDG_CURRENT_DESKTOP" != "GNOME" ] && [ "$XDG_CURRENT_DESKTOP" != "ubuntu:GNOME" ]; then
    print_error "GNOME desktop environment not detected"
    print_info "Current desktop: $XDG_CURRENT_DESKTOP"
    print_info "Please set up the keyboard shortcut manually:"
    print_info "Command: uv run python -m f9_asr.main"
    print_info "Key: F9"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Get absolute path to main.py
MAIN_SCRIPT="$PROJECT_DIR/src/f9_asr/main.py"

if [ ! -f "$MAIN_SCRIPT" ]; then
    print_error "Main script not found: $MAIN_SCRIPT"
    exit 1
fi

# Get absolute path to uv (if available) or python
if command -v uv &> /dev/null; then
    COMMAND="cd $PROJECT_DIR && uv run python -m f9_asr.main"
else
    COMMAND="cd $PROJECT_DIR && python3 -m f9_asr.main"
fi

print_info "Setting up F9 keyboard shortcut..."

# Get existing custom keybindings
EXISTING_BINDINGS=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings 2>/dev/null || echo "[]")

# Check if binding already exists
if echo "$EXISTING_BINDINGS" | grep -q "f9-asr"; then
    print_info "F9 ASR keybinding already exists, updating..."
    KEYBINDING_PATH="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/f9-asr/"
else
    # Create new binding path
    KEYBINDING_PATH="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/f9-asr/"
    
    # Add to existing bindings
    NEW_BINDINGS=$(echo "$EXISTING_BINDINGS" | sed 's/]$/, '\''\/org\/gnome\/settings-daemon\/plugins\/media-keys\/custom-keybindings\/f9-asr\/'\'']/')
    if [ "$NEW_BINDINGS" = "$EXISTING_BINDINGS" ]; then
        # Empty list case
        NEW_BINDINGS="['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/f9-asr/']"
    fi
    
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_BINDINGS"
fi

# Set keybinding properties
gsettings set "$KEYBINDING_PATH" name 'F9 ASR Transcription'
gsettings set "$KEYBINDING_PATH" command "$COMMAND"
gsettings set "$KEYBINDING_PATH" binding 'F9'

print_status "F9 hotkey configured"
print_info ""
print_info "Usage:"
print_info "1. Press F9 to start recording"
print_info "2. Speak into your microphone"
print_info "3. Press F9 again to stop and transcribe"
print_info "4. The text will be copied to your clipboard"
print_info ""
print_info "Note: You may need to log out and back in for the hotkey to take effect"
print_info "Or restart GNOME: Alt+F2 → r → Enter"
