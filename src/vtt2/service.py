"""
launchd service management for VTT2.
Install / uninstall / status for menubar (ai.vtt2) and STT HTTP (ai.vtt2.stt).
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)

UI_LABEL = "ai.vtt2"
STT_LABEL = "ai.vtt2.stt"
UI_PLIST_NAME = f"{UI_LABEL}.plist"
STT_PLIST_NAME = f"{STT_LABEL}.plist"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
INSTALLED_UI_PLIST = LAUNCH_AGENTS_DIR / UI_PLIST_NAME
INSTALLED_STT_PLIST = LAUNCH_AGENTS_DIR / STT_PLIST_NAME

# Back-compat aliases used by older call sites / docs
LABEL = UI_LABEL
PLIST_NAME = UI_PLIST_NAME
INSTALLED_PLIST = INSTALLED_UI_PLIST


def _project_root() -> Path:
    """Return the project root (two levels up from this file: src/vtt2/service.py)."""
    return Path(__file__).resolve().parent.parent.parent


def _find_uv() -> str:
    """Locate the uv binary."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    for candidate in [
        Path.home() / ".cargo" / "bin" / "uv",
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
        Path.home() / ".local" / "bin" / "uv",
    ]:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        "uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"
    )


def _load_env_vtt2() -> dict[str, str]:
    """Load KEY=VALUE from .env.vtt2 (gitignored)."""
    env_file = _project_root() / ".env.vtt2"
    if not env_file.exists():
        return {}
    result = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip().strip("'\"").replace('\\"', '"')
    return result


def _env_vars_xml(env: dict[str, str]) -> str:
    """Generate plist EnvironmentVariables block."""
    if not env:
        return ""
    lines = [
        "    <key>EnvironmentVariables</key>",
        "    <dict>",
    ]
    for k, v in env.items():
        escaped = v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"        <key>{k}</key>")
        lines.append(f"        <string>{escaped}</string>")
    lines.append("    </dict>")
    return "\n".join(lines) + "\n\n"


def _render_plist(plist_name: str) -> str:
    """Read template plist and replace placeholders."""
    template_path = _project_root() / "service" / plist_name
    if not template_path.exists():
        raise FileNotFoundError(f"Plist template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    env = _load_env_vtt2()
    # Menubar must use local_stt client; do not force mlx_whisper via stale env
    if plist_name == UI_PLIST_NAME:
        env.pop("VTT2_TRANSCRIPTION_ENGINE", None)
    env_xml = _env_vars_xml(env)

    replacements = {
        "__UV_PATH__": _find_uv(),
        "__PROJECT_DIR__": str(_project_root()),
        "__HOME__": str(Path.home()),
        "__ENV_VARS_XML__": env_xml,
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content


def _unload(plist_path: Path) -> None:
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True,
        )


def _load(plist_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True,
        text=True,
    )


def is_orphan_menubar_cmdline(cmdline: list[str] | None) -> bool:
    """True for leftover menubar python — never the STT server or --install itself."""
    if not cmdline:
        return False
    joined = " ".join(str(part) for part in cmdline).replace("\\", "/")
    if "--serve-stt" in joined:
        return False
    if any(
        flag in joined
        for flag in ("--install", "--uninstall", "--status", "--health")
    ):
        return False
    return "vtt2/main.py" in joined


def kill_orphan_menubar(*, current_pid: int | None = None) -> list[int]:
    """Terminate leftover menubar processes (PPID 1 after reload). Not --serve-stt."""
    current = os.getpid() if current_pid is None else current_pid
    killed: list[int] = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = proc.info["pid"]
            if pid == current:
                continue
            if not is_orphan_menubar_cmdline(proc.info.get("cmdline")):
                continue
            print(f"  Stopping leftover menubar PID {pid}")
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            killed.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def clear_menubar_pid_file() -> None:
    """Drop menubar pid-file so the freshly loaded UI can acquire it."""
    from utils.pid_manager import PID_FILE

    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)
        print(f"  Removed stale PID file: {PID_FILE}")


def _install_one(
    label: str,
    plist_name: str,
    installed: Path,
    *,
    before_load=None,
) -> int:
    print(f"Installing {label}...")
    _unload(installed)
    if before_load is not None:
        before_load()
    try:
        content = _render_plist(plist_name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    installed.write_text(content, encoding="utf-8")
    print(f"  Plist written to {installed}")
    result = _load(installed)
    if result.returncode != 0:
        print(
            f"  Warning: launchctl load returned {result.returncode}: "
            f"{(result.stderr or '').strip()}"
        )
    else:
        print("  Service loaded successfully.")
    return 0


def _prepare_ui_reload() -> None:
    """Kill orphan menubar and clear pid so --install always picks up new local_stt."""
    killed = kill_orphan_menubar()
    if killed:
        print(f"  Stopped leftover menubar PIDs: {killed}")
    clear_menubar_pid_file()


def install_service() -> int:
    """Install STT then menubar LaunchAgents."""
    print("Installing VTTv2 services (STT + menubar)...")
    log_dir = Path.home() / "Library" / "Logs" / "vtt2"
    log_dir.mkdir(parents=True, exist_ok=True)

    env_vtt2 = _load_env_vtt2()
    if env_vtt2:
        print(f"  .env.vtt2: загружено {len(env_vtt2)} переменных")

    # STT first — owns the model; menubar is the client
    rc = _install_one(STT_LABEL, STT_PLIST_NAME, INSTALLED_STT_PLIST)
    if rc != 0:
        return rc
    rc = _install_one(
        UI_LABEL,
        UI_PLIST_NAME,
        INSTALLED_UI_PLIST,
        before_load=_prepare_ui_reload,
    )
    if rc != 0:
        return rc

    print()
    print("Both services start on login.")
    print("  STT API: http://127.0.0.1:8765  (see docs/STT_API.md)")
    print("  Stop STT:  launchctl unload ~/Library/LaunchAgents/ai.vtt2.stt.plist")
    print("  Stop UI:   launchctl unload ~/Library/LaunchAgents/ai.vtt2.plist")
    print("  Logs:      ~/Library/Logs/vtt2/")
    return 0


def uninstall_service() -> int:
    """Uninstall both LaunchAgents."""
    print("Uninstalling VTTv2 services...")
    for label, path in (
        (UI_LABEL, INSTALLED_UI_PLIST),
        (STT_LABEL, INSTALLED_STT_PLIST),
    ):
        print(f"  {label}...")
        if not path.exists():
            print("    not installed")
            continue
        _unload(path)
        path.unlink(missing_ok=True)
        print("    uninstalled")
    return 0


def _print_one_status(label: str, installed: Path) -> None:
    print(f"{label}:")
    if not installed.exists():
        print("  Installed: No")
        return
    print(f"  Installed: Yes ({installed})")
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        # Exact label match (avoid ai.vtt2 matching ai.vtt2.stt)
        parts = line.split()
        if len(parts) >= 3 and parts[2] == label:
            pid = parts[0] if parts[0] != "-" else "not running"
            exit_code = parts[1]
            print(f"  PID: {pid}")
            print(f"  Last exit code: {exit_code}")
            break
    else:
        print(f"  Status: not loaded (launchctl load {installed})")


def service_status() -> int:
    """Show STT + menubar status."""
    print("VTTv2 service status:")
    print()
    _print_one_status(STT_LABEL, INSTALLED_STT_PLIST)
    print()
    _print_one_status(UI_LABEL, INSTALLED_UI_PLIST)
    print()
    log_dir = Path.home() / "Library" / "Logs" / "vtt2"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"))
        if log_files:
            print(f"Logs: {log_dir}")
            for lf in log_files:
                size_kb = lf.stat().st_size / 1024
                print(f"  {lf.name} ({size_kb:.0f} KB)")
    return 0
