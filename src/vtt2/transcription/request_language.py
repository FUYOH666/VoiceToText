"""Resolve POST /v1/audio/transcriptions language into a Whisper code.

The HTTP contract is canonical codes plus ``auto``. Full names such as
``Thai`` are rejected here on purpose: mlx-whisper can map them, this API does not.
"""
from __future__ import annotations

from typing import Optional

_CODES: Optional[frozenset[str]] = None


class RejectedLanguage(ValueError):
    """Client sent a language token this API does not accept."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        super().__init__(
            "language must be a canonical code (for example en, ru, th) or auto"
        )


def _canonical_codes() -> frozenset[str]:
    global _CODES
    if _CODES is None:
        from mlx_whisper.tokenizer import LANGUAGES

        _CODES = frozenset(LANGUAGES)
    return _CODES


def config_language(config_value: Optional[str]) -> Optional[str]:
    """Config value for Whisper. ``auto`` and blank become None (autodetect)."""
    if config_value is None:
        return None
    token = config_value.strip().lower()
    if not token or token == "auto":
        return None
    return token


def resolve_request_language(
    raw: Optional[str],
    config_value: Optional[str],
) -> tuple[str, Optional[str]]:
    """Return ``(requested_label, effective_language)``.

    ``effective_language`` is what ``mlx_whisper.transcribe`` receives.
    ``None`` means autodetect. Override happens only for an explicit code or ``auto``.

    - field omitted → config
    - empty or whitespace → config (not autodetect)
    - ``auto`` → None
    - canonical code → that code
    - anything else → RejectedLanguage
    """
    if raw is None:
        return "omitted", config_language(config_value)
    if not raw.strip():
        return "blank", config_language(config_value)
    token = raw.strip().lower()
    if token == "auto":
        return "auto", None
    if token in _canonical_codes():
        return token, token
    raise RejectedLanguage(raw)
