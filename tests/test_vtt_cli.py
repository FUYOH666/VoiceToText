"""Smoke tests for unified vtt CLI."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_validate_config_subprocess():
    result = subprocess.run(
        [sys.executable, "-m", "vtt.cli", "validate-config"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "OK" in result.stdout
