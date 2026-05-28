"""
launchd service management for VTT2.
Install / uninstall / status via LaunchAgent plist.
"""
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

LABEL = "ai.vtt2"
PLIST_NAME = f"{LABEL}.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
INSTALLED_PLIST = LAUNCH_AGENTS_DIR / PLIST_NAME


def _project_root() -> Path:
    """Return the project root (two levels up from this file: src/vtt2/service.py)."""
    return Path(__file__).resolve().parent.parent.parent


def _find_uv() -> str | None:
    """Locate the uv binary. Returns None if not found."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    for candidate in [
        Path.home() / ".cargo" / "bin" / "uv",
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def _program_args() -> list[str]:
    """Return ProgramArguments for launchd: [executable, ...args] to run main.py."""
    project = _project_root()
    main_script = str(project / "src" / "vtt2" / "main.py")
    venv_python = project / ".venv" / "bin" / "python"

    # Prefer .venv directly — avoids uv sync (which can fail on rumps/build)
    if venv_python.exists():
        base_cmd = [str(venv_python), main_script]
    else:
        uv_path = _find_uv()
        if uv_path:
            base_cmd = [uv_path, "run", "python", main_script]
        else:
            base_cmd = [sys.executable, main_script]

    # Wrapper: sleep 5s before start (lets GUI session initialize at login)
    import shlex
    safe_cmd = " ".join(shlex.quote(a) for a in base_cmd)
    return ["/bin/sh", "-c", f"sleep 5 && exec {safe_cmd}"]


def _render_plist() -> str:
    """Generate plist content with real paths."""
    project = str(_project_root())
    home = str(Path.home())
    log_dir = Path(home) / "Library" / "Logs" / "vtt2"

    args = _program_args()
    args_xml = "\n".join(f'        <string>{a}</string>' for a in args)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>

    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>

    <key>WorkingDirectory</key>
    <string>{project}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>VTT2_LAUNCHD</key>
        <string>1</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>LimitLoadToSessionType</key>
    <array>
        <string>Aqua</string>
    </array>

    <key>StandardOutPath</key>
    <string>{log_dir}/vtt2.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/vtt2.stderr.log</string>

    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""


def install_service() -> int:
    """Install VTT2 as a launchd LaunchAgent."""
    print(f"Installing VTT2 service ({LABEL})...")

    uv_path = _find_uv()
    if uv_path:
        print(f"  Using: uv run python")
    else:
        print(f"  Using: {sys.executable} (uv not found)")

    # Unload if already installed
    if INSTALLED_PLIST.exists():
        subprocess.run(
            ["launchctl", "unload", str(INSTALLED_PLIST)],
            capture_output=True,
        )

    # Render and write plist
    plist_content = _render_plist()

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
