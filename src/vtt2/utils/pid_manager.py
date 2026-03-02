"""
PID file management for single-instance protection.
Prevents multiple VTT2 instances from running simultaneously.
"""
import logging
import os
import signal
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)

PID_DIR = Path.home() / ".local" / "state" / "vtt2"
PID_FILE = PID_DIR / "vtt2.pid"


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is alive and is a VTT2 process."""
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        return "vtt2" in cmdline or "main.py" in cmdline
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def acquire_pid_file() -> bool:
    """
    Try to acquire the PID file. Returns True if successful.
    If another VTT2 instance is running, logs an error and returns False.
    Removes stale PID files automatically.
    """
    PID_DIR.mkdir(parents=True, exist_ok=True)

    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            old_pid = -1

        if old_pid > 0 and _is_process_alive(old_pid):
            logger.error(
                f"Another VTT2 instance is already running (PID {old_pid}). "
                "Stop it first or remove the PID file: %s",
                PID_FILE,
            )
            return False

        logger.warning("Removing stale PID file (PID %s no longer running)", old_pid)
        PID_FILE.unlink(missing_ok=True)

    PID_FILE.write_text(str(os.getpid()))
    logger.debug("PID file created: %s (PID %s)", PID_FILE, os.getpid())
    return True


def release_pid_file() -> None:
    """Remove the PID file on shutdown."""
    try:
        if PID_FILE.exists():
            stored_pid = int(PID_FILE.read_text().strip())
            if stored_pid == os.getpid():
                PID_FILE.unlink(missing_ok=True)
                logger.debug("PID file removed: %s", PID_FILE)
    except (ValueError, OSError) as exc:
        logger.debug("Could not remove PID file: %s", exc)
