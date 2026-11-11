"""Curated model catalog + user additions, memory-aware recommendation.

A model is identified by a catalog id (``qwen3-asr-1.7b-8bit``). Choosing one
means: ``stt_server.engine`` = its family and
``transcription.<family>.model_name`` = its Hugging Face repo. The choice is
persisted in the user overlay (``~/Library/Application Support/VoiceToText/
config.yaml``), never in the git-tracked repo ``config.yaml``.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).with_name("catalog.yaml")
FAMILIES = ("qwen3_asr", "mlx_whisper")

# What each library actually loads; keeps downloads to the needed files.
ALLOW_PATTERNS: dict[str, list[str]] = {
    "qwen3_asr": ["*.json", "*.safetensors", "*.txt", "*.model"],
    "mlx_whisper": ["*.json", "*.safetensors", "*.npz", "*.tiktoken", "*.txt"],
}
_WEIGHT_SUFFIXES = (".safetensors", ".npz")


@dataclass(frozen=True)
class ModelSpec:
    id: str
    title: str
    family: str
    repo: str
    quantization: str = "unknown"
    download_gb: float = 0.0
    ram_gb: float = 0.0
    min_memory_gb: float = 0.0
    languages: str = ""
    note: str = ""
    verified_revision: Optional[str] = None
    # Whisper's built-in speech → English translation works well (large-v3, small);
    # turbo was trained for transcription only.
    translates: bool = False
    custom: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Catalog:
    models: list[ModelSpec]
    rules: list[tuple[float, str]]  # (min_memory_gb, model id), checked in order

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return next((m for m in self.models if m.id == model_id), None)

    def find(self, family: str, repo: str) -> Optional[ModelSpec]:
        return next((m for m in self.models if m.family == family and m.repo == repo), None)

    def recommended(self, memory_gb: float) -> Optional[str]:
        for min_gb, model_id in self.rules:
            if memory_gb >= min_gb and self.get(model_id) is not None:
                return model_id
        return None


# --- paths -------------------------------------------------------------------


def user_dir() -> Path:
    """Per-user state. ``VTT2_USER_DIR`` overrides it (tests, portable installs)."""
    override = os.environ.get("VTT2_USER_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "VoiceToText"


def user_config_path() -> Path:
    from config.loader import user_overlay_path

    return user_overlay_path()


def user_models_path() -> Path:
    return user_dir() / "models.yaml"


# --- catalog -----------------------------------------------------------------


def _spec_from(raw: dict[str, Any], *, custom: bool = False) -> ModelSpec:
    family = raw.get("family")
    if family not in FAMILIES:
        raise ValueError(f"model {raw.get('id')!r}: unknown family {family!r}")
    for key in ("id", "title", "repo"):
        if not raw.get(key):
            raise ValueError(f"model entry is missing {key!r}: {raw}")
    known = {f for f in ModelSpec.__dataclass_fields__}
    data = {k: v for k, v in raw.items() if k in known}
    data["custom"] = custom
    return ModelSpec(**data)


def load_catalog(
    path: Path = CATALOG_PATH,
    user_path: Optional[Path] = None,
) -> Catalog:
    """Shipped catalog plus the user's custom models (custom ids never shadow shipped ones)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    models = [_spec_from(entry) for entry in raw.get("models") or []]
    ids = {m.id for m in models}
    if len(ids) != len(models):
        raise ValueError("duplicate model ids in catalog")
    rules = [(float(r["min_memory_gb"]), str(r["model"])) for r in raw.get("recommended") or []]
    rules.sort(key=lambda rule: rule[0], reverse=True)

    user_path = user_models_path() if user_path is None else user_path
    if user_path.is_file():
        try:
            extra = yaml.safe_load(user_path.read_text(encoding="utf-8")) or {}
            for entry in extra.get("models") or []:
                spec = _spec_from(entry, custom=True)
                if spec.id in ids:
                    continue
                models.append(spec)
                ids.add(spec.id)
        except Exception as exc:  # a broken user file must not take the server down
            logger.warning("Ignoring %s: %s", user_path, exc)
    return Catalog(models=models, rules=rules)


def add_user_model(spec: ModelSpec, path: Optional[Path] = None) -> None:
    path = user_models_path() if path is None else path
    data: dict[str, Any] = {}
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = [e for e in data.get("models") or [] if e.get("id") != spec.id]
    entry = {k: v for k, v in spec.to_dict().items() if k != "custom" and v not in (None, "")}
    entries.append(entry)
    data["models"] = entries
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def custom_id(repo: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", repo.split("/")[-1].lower()).strip("-")
    return f"custom-{slug or 'model'}"


# --- machine and cache -----------------------------------------------------------


def system_memory_gb() -> float:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError):
        return 0.0


def local_snapshot(repo: str) -> Optional[Path]:
    """The cached snapshot of ``repo`` if its weights are on disk (no network)."""
    from transcription.hf_cache import resolve_cached_snapshot

    resolved = resolve_cached_snapshot(repo)
    if resolved == repo:
        return None
    path = Path(resolved)
    if any(path.glob(f"*{suffix}") for suffix in _WEIGHT_SUFFIXES):
        return path
    return None


def is_installed(spec: ModelSpec) -> bool:
    return local_snapshot(spec.repo) is not None


# --- config ------------------------------------------------------------------


def active_selection(config) -> tuple[str, str]:
    """(family, repo) the server is configured to load."""
    family = config.stt_server.engine
    section = getattr(config.transcription, family, None)
    repo = getattr(section, "model_name", "") if section is not None else ""
    return family, repo


def selection_overlay(spec: ModelSpec) -> dict[str, Any]:
    """The keys that select ``spec``; written to the user overlay on activation."""
    section: dict[str, Any] = {"model_name": spec.repo}
    if spec.family == "qwen3_asr" and spec.quantization in ("8bit", "4bit"):
        # Already quantized on disk; quantizing again in memory would fail.
        section["quantization_bits"] = None
    return {
        "stt_server": {"engine": spec.family},
        "transcription": {spec.family: section},
    }


def config_with(config, spec: ModelSpec):
    """A copy of ``config`` that loads ``spec``."""
    from config.loader import Config, deep_merge

    data = config.model_dump()
    return Config(**deep_merge(data, selection_overlay(spec)))


def write_selection(spec: ModelSpec, path: Optional[Path] = None) -> Path:
    """Merge the selection into the user overlay file, keeping its other keys."""
    from config.loader import deep_merge

    path = user_config_path() if path is None else path
    current: dict[str, Any] = {}
    if path.is_file():
        current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    merged = deep_merge(current, selection_overlay(spec))
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# VoiceToText user settings (written by the app). Overrides the repo config.yaml.\n"
    )
    path.write_text(header + yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def describe(spec: ModelSpec, *, memory_gb: float, recommended_id: Optional[str], active: bool) -> dict:
    data = spec.to_dict()
    data.update(
        {
            "object": "model",
            "installed": is_installed(spec),
            "active": active,
            "recommended": spec.id == recommended_id,
            "fits_memory": memory_gb <= 0 or memory_gb >= spec.min_memory_gb,
        }
    )
    return data


def replace_spec(spec: ModelSpec, **changes: Any) -> ModelSpec:
    return replace(spec, **changes)
