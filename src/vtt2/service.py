"""
launchd service management for VTT2.
Install / uninstall / status via LaunchAgent plist.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

LABEL = "ai.vtt2"
PLIST_NAME = f"{LABEL}.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
INSTALLED_PLIST = LAUNCH_AGENTS_DIR / PLIST_NAME


def _project_root() -> Path:
    """Return the project root (two levels up from this file: src/vtt2/service.py)."""
    return Path(__file__).resolve().parent.parent.parent


def _find_uv() -> str:
    """Locate the uv binary."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    # Common Homebrew / cargo locations
    for candidate in [
        Path.home() / ".cargo" / "bin" / "uv",
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
    ]:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"
    )


def _render_plist() -> str:
    """Read the template plist and replace placeholders with real paths."""
    template_path = _project_root() / "service" / PLIST_NAME
    if not template_path.exists():
        raise FileNotFoundError(f"Plist template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    replacements = {
        "__UV_PATH__": _find_uv(),
        "__PROJECT_DIR__": str(_project_root()),
        "__HOME__": str(Path.home()),
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content


def install_service() -> int:
    """Install VTT2 as a launchd LaunchAgent."""
    print(f"Installing VTT2 service ({LABEL})...")

    # Unload if already installed
    if INSTALLED_PLIST.exists():
        subprocess.run(
            ["launchctl", "unload", str(INSTALLED_PLIST)],
            capture_output=True,
        )

    # Render and write plist
    try:
        plist_content = _render_plist()
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1

    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    INSTALLED_PLIST.write_text(plist_content, encoding="utf-8")
    print(f"  Plist written to {INSTALLED_PLIST}")

    # Create log directory
    log_dir = Path.home() / "Library" / "Logs" / "vtt2"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Load the service
    result = subprocess.run(
        ["launchctl", "load", str(INSTALLED_PLIST)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Warning: launchctl load returned {result.returncode}: {result.stderr.strip()}")
    else:
        print("  Service loaded successfully.")

    print()
    print("VTT2 will now start automatically on login.")
    print("  Stop:    launchctl unload ~/Library/LaunchAgents/ai.vtt2.plist")
    print("  Start:   launchctl load   ~/Library/LaunchAgents/ai.vtt2.plist")
    print("  Logs:    ~/Library/Logs/vtt2/")
    return 0


def uninstall_service() -> int:
    """Uninstall the VTT2 LaunchAgent."""
    print(f"Uninstalling VTT2 service ({LABEL})...")

    if not INSTALLED_PLIST.exists():
        print("  Service is not installed.")
        return 0

    result = subprocess.run(
        ["launchctl", "unload", str(INSTALLED_PLIST)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Warning: launchctl unload returned {result.returncode}: {result.stderr.strip()}")

    INSTALLED_PLIST.unlink(missing_ok=True)
    print("  Service uninstalled. It will no longer start on login.")
    return 0


def service_status() -> int:
    """Show current VTT2 service status."""
    print(f"VTT2 service status ({LABEL}):")
    print()

    if not INSTALLED_PLIST.exists():
        print("  Installed: No")
        return 0

    print(f"  Installed: Yes ({INSTALLED_PLIST})")

    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if LABEL in line:
            parts = line.split()
            pid = parts[0] if parts[0] != "-" else "not running"
            exit_code = parts[1] if len(parts) > 1 else "?"
            print(f"  PID: {pid}")
            print(f"  Last exit code: {exit_code}")
            break
    else:
        print("  Status: not loaded (run: launchctl load ~/Library/LaunchAgents/ai.vtt2.plist)")

    # Log files
    log_dir = Path.home() / "Library" / "Logs" / "vtt2"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"))
        if log_files:
            print(f"  Logs: {log_dir}")
            for lf in log_files:
                size_kb = lf.stat().st_size / 1024
                print(f"    {lf.name} ({size_kb:.0f} KB)")
    return 0
