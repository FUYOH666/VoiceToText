"""
F9 Linux client configuration (separate schema from VTT2 Mac Config).
Loads config/base is NOT used — only config/profiles/linux-f9-*.yaml overlays.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from config.merge import deep_merge

logger = logging.getLogger(__name__)

F9_PROFILE_PREFIX = "linux-f9"
VALID_F9_PROFILES = ("linux-f9-local", "linux-f9-edge")


class ASRConfig(BaseModel):
    base_url: str = Field("http://127.0.0.1:8001")
    transcription_endpoint: str = Field("/v1/audio/transcriptions")
    timeout: int = Field(30, ge=10, le=300)
    language: Optional[str] = None
    response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "json"


class HotkeyConfig(BaseModel):
    key: str = Field("f9")
    pid_file: str = Field("/tmp/f9-asr-recording.pid")


class F9Config(BaseModel):
    asr: ASRConfig
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)

    @classmethod
    def resolve_profile_name(
        cls,
        profile: Optional[str] = None,
        env_profile: bool = True,
    ) -> str:
        if profile:
            return profile
        if env_profile:
            from_env = os.getenv("VTT2_PROFILE") or os.getenv("F9_PROFILE")
            if from_env:
                return from_env
        return "linux-f9-local"

    @classmethod
    def from_profile(
        cls,
        project_root: Path,
        profile: Optional[str] = None,
    ) -> "F9Config":
        profile_name = cls.resolve_profile_name(profile)
        if profile_name not in VALID_F9_PROFILES:
            raise ValueError(
                f"Unknown F9 profile {profile_name!r}; expected one of {VALID_F9_PROFILES}"
            )
        base_path = project_root / "config" / "f9_base.yaml"
        profile_path = project_root / "config" / "profiles" / f"{profile_name}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"F9 profile not found: {profile_path}")

        data: dict[str, Any] = {}
        if base_path.is_file():
            with open(base_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        with open(profile_path, encoding="utf-8") as f:
            profile_data = yaml.safe_load(f) or {}
        data = deep_merge(data, profile_data)

        cls._load_env_file(project_root / ".env.local")
        data = cls._apply_local_ai_asr_env(data, profile_name=profile_name)

        return cls(**data)

    @classmethod
    def load_merged_dict(
        cls,
        project_root: Path,
        profile: Optional[str] = None,
    ) -> dict[str, Any]:
        """Merged YAML dict for f9_asr.config.Config.from_dict()."""
        cfg = cls.from_profile(project_root, profile=profile)
        return cfg.model_dump()

    @staticmethod
    def _load_env_file(path: Path) -> None:
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    @staticmethod
    def _apply_local_ai_asr_env(
        data: dict[str, Any],
        *,
        profile_name: str,
    ) -> dict[str, Any]:
        """Apply LOCAL_AI_ASR_* only for edge profile (parity with Mac remote_asr)."""
        if "asr" not in data:
            data["asr"] = {}
        asr = data["asr"]
        yaml_url = str(asr.get("base_url", ""))
        use_env = profile_name == "linux-f9-edge" or "YOUR_ASR_HOST" in yaml_url
        if not use_env:
            return data

        base_url = os.getenv("LOCAL_AI_ASR_BASE_URL", "").strip()
        if base_url:
            asr["base_url"] = base_url.rstrip("/")
        timeout = os.getenv("LOCAL_AI_ASR_TIMEOUT")
        if timeout:
            try:
                asr["timeout"] = int(timeout)
            except ValueError:
                pass
        lang = os.getenv("LOCAL_AI_ASR_DEFAULT_LANGUAGE")
        if lang:
            asr["language"] = lang
        return data
