"""Tests for Linux F9 profile loader."""
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "src" / "vtt2"))

from config.f9_loader import F9Config, VALID_F9_PROFILES


class TestF9Config:
    def test_linux_f9_local_profile(self, project_root, monkeypatch):
        monkeypatch.delenv("LOCAL_AI_ASR_BASE_URL", raising=False)
        cfg = F9Config.from_profile(project_root, profile="linux-f9-local")
        assert cfg.asr.base_url == "http://127.0.0.1:8001"
        assert cfg.hotkey.key == "f9"

    def test_linux_f9_local_ignores_env_url(self, project_root, monkeypatch):
        monkeypatch.setenv("LOCAL_AI_ASR_BASE_URL", "http://tailscale-host.example:8001")
        cfg = F9Config.from_profile(project_root, profile="linux-f9-local")
        assert cfg.asr.base_url == "http://127.0.0.1:8001"

    def test_linux_f9_edge_uses_env_url(self, project_root, monkeypatch):
        monkeypatch.setenv("LOCAL_AI_ASR_BASE_URL", "http://tailscale-host.example:8001")
        cfg = F9Config.from_profile(project_root, profile="linux-f9-edge")
        assert cfg.asr.base_url == "http://tailscale-host.example:8001"

    def test_valid_profiles_constant(self):
        assert "linux-f9-local" in VALID_F9_PROFILES
        assert "linux-f9-edge" in VALID_F9_PROFILES
