#!/bin/bash

# Install F9 ASR as systemd user service
# Установка F9 ASR как systemd user service

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_FILE="$SCRIPT_DIR/f9-asr.service"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root. It will install a user service."
    exit 1
fi

# Get current user
CURRENT_USER="$USER"
USER_HOME="$HOME"

print_info "Installing F9 ASR systemd user service for user: $CURRENT_USER"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed or not in PATH"
    print_info "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if ASR service is running
print_info "Checking ASR service availability..."
if ! curl -s http://localhost:8001/healthz &> /dev/null; then
    print_error "ASR service is not available on port 8001"
    print_info "Please ensure the ASR service is running before installing F9 ASR"
    exit 1
fi
print_status "ASR service is available"

# Create systemd user directory if it doesn't exist
SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
print_status "Systemd user directory ready: $SYSTEMD_USER_DIR"

# Copy service file and replace placeholders
SERVICE_TARGET="$SYSTEMD_USER_DIR/f9-asr.service"
# Find uv path
UV_PATH=$(which uv || echo "$HOME/.local/bin/uv")
# Get absolute path to project directory
PROJECT_DIR_ABS=$(cd "$PROJECT_DIR" && pwd)
LAUNCH_SCRIPT="$PROJECT_DIR_ABS/scripts/f9-asr-launch.sh"
chmod +x "$LAUNCH_SCRIPT"

# Create service file with proper paths
{
    sed "s|%h|$USER_HOME|g" "$SERVICE_FILE" | \
    sed "s|PLACEHOLDER_LAUNCH|$LAUNCH_SCRIPT|g" | \
    awk -v wd="$PROJECT_DIR_ABS" '
        /^ExecStart=/ && !wd_set {
            print "WorkingDirectory=" wd
            wd_set=1
        }
        {print}
    '
} > "$SERVICE_TARGET"

print_status "Service file installed: $SERVICE_TARGET"
print_info "Using uv at: $UV_PATH"
print_info "Working directory: $PROJECT_DIR_ABS"

# Reload systemd user daemon
print_info "Reloading systemd user daemon..."
systemctl --user daemon-reload
print_status "Systemd daemon reloaded"

# Enable service for autostart
print_info "Enabling service for autostart..."
systemctl --user enable f9-asr.service
print_status "Service enabled for autostart"

# Start service
print_info "Starting service..."
if systemctl --user start f9-asr.service; then
    print_status "Service started successfully"
else
    print_error "Failed to start service"
    print_info "Check status with: systemctl --user status f9-asr.service"
    print_info "Check logs with: journalctl --user -u f9-asr.service -f"
    exit 1
fi

# Wait a moment and check status
sleep 2
if systemctl --user is-active --quiet f9-asr.service; then
    print_status "Service is running"
else
    print_error "Service is not running"
    print_info "Check logs: journalctl --user -u f9-asr.service --no-pager -n 50"
    exit 1
fi

print_info ""
print_status "Installation complete!"
print_info ""
print_info "Service management commands:"
print_info "  Start:   systemctl --user start f9-asr.service"
print_info "  Stop:    systemctl --user stop f9-asr.service"
print_info "  Restart: systemctl --user restart f9-asr.service"
print_info "  Status:  systemctl --user status f9-asr.service"
print_info "  Logs:    journalctl --user -u f9-asr.service -f"
print_info ""
print_info "The service will automatically start on login and restart if it crashes."
print_info "Press F9 to start/stop voice transcription!"
