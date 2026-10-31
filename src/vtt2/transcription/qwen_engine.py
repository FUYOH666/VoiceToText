"""Optional Qwen3-ASR engine for the same STT process as MLX Whisper.

The package is an extra (`uv sync --extra qwen`). Import happens only when
this engine is constructed. A missing extra is an error — there is no
fallback to Whisper.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

QWEN_EXTRA_MISSING = (
    "mlx-qwen3-asr is not installed. "
    "Install the optional extra: uv sync --extra qwen"
)

# Caller omitted language. None means autodetect and must not be collapsed into this.
_CONFIG_LANGUAGE = object()


def ensure_qwen_installed() -> None:
    """Raise if the optional extra is not installed."""
    try:
        import mlx_qwen3_asr  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(QWEN_EXTRA_MISSING) from exc


def library_language_name(code: str | None) -> str | None:
    """Map an API language code to the name mlx-qwen3-asr puts in the prompt.

    ``None`` and ``auto`` leave detection to the library. Codes in the
    library alias table (``ru`` → ``Russian``) use that table. Other canonical
    codes, including ``th``, use the English name from the Whisper code list
    (``Thai``). The library may warn if a checkpoint does not list that name.
    """
    if code is None:
        return None
    token = str(code).strip().lower()
    if not token or token == "auto":
        return None
    from mlx_qwen3_asr.tokenizer import canonicalize_language, language_is_known

    if language_is_known(token):
        return canonicalize_language(token)
    from mlx_whisper.tokenizer import LANGUAGES

    label = LANGUAGES.get(token)
    if isinstance(label, str) and label.strip():
        return label.strip().title()
    return token


def reported_language(
    library_name: str | None,
    effective_code: str | None,
) -> str | None:
    """ISO code for the HTTP body. A forced code wins over the library's English name."""
    if effective_code:
        return effective_code
    if not library_name:
        return None
    key = str(library_name).strip().lower()
    if not key or key == "unknown":
        return None
    from mlx_whisper.tokenizer import LANGUAGES

    for code, label in LANGUAGES.items():
        if code == key or str(label).lower() == key:
            return code
    return key


class Qwen3ASRTranscriber:
    """One Qwen3-ASR checkpoint. Quantization, when set, runs in this process."""

    def __init__(self, config):
        ensure_qwen_installed()
        qcfg = getattr(config.transcription, "qwen3_asr", None)
        if qcfg is None:
            raise RuntimeError("qwen3_asr engine requires transcription.qwen3_asr")
        self.config = config
        self.qcfg = qcfg
        self.sample_rate = 16000
        self._model = None
        logger.info(
            "Qwen3ASRTranscriber: model=%s quantization_bits=%s",
            qcfg.model_name,
            qcfg.quantization_bits,
        )

    def release(self) -> None:
        """Drop the in-process weights so idle unload can free them."""
        self._model = None
        try:
            from mlx_qwen3_asr.load_models import _ModelHolder

            _ModelHolder.clear()
        except Exception:
            logger.debug("qwen model holder clear skipped", exc_info=True)
        try:
            from mlx_qwen3_asr.tokenizer import _TokenizerHolder

            _TokenizerHolder.clear()
        except Exception:
            logger.debug("qwen tokenizer holder clear skipped", exc_info=True)

    def transcribe(self, audio_data: np.ndarray) -> str:
        return self.transcribe_detailed(audio_data)["text"]

    def transcribe_detailed(
        self,
        audio_data: np.ndarray,
        *,
        word_timestamps: bool = False,
        language: object = _CONFIG_LANGUAGE,
        requested_language: str | None = None,
        initial_prompt: str | None = None,
    ) -> dict:
        from transcription.request_language import config_language

        if language is _CONFIG_LANGUAGE:
            effective = config_language(self.qcfg.language)
            requested_label = requested_language or "omitted"
        elif language is None or isinstance(language, str):
            effective = language
            requested_label = requested_language or (
                "auto" if effective is None else effective
            )
        else:
            raise TypeError("language must be a code, None, or omitted")

        duration = len(audio_data) / float(self.sample_rate) if len(audio_data) else 0.0
        prompt = (initial_prompt or "").strip() or ""
        library_language = library_language_name(effective)
        logger.info(
            "Qwen3-ASR detailed: %.1fs audio word_timestamps=%s "
            "requested_language=%s effective_language=%s",
            duration,
            word_timestamps,
            requested_label,
            "None" if effective is None else effective,
        )
        try:
            from mlx_qwen3_asr import transcribe as qwen_transcribe

            result = qwen_transcribe(
                _as_float32(audio_data),
                model=self._ensure_model(),
                language=library_language,
                return_timestamps=bool(word_timestamps),
                return_chunks=True,
                context=prompt,
                verbose=False,
            )
        except Exception as exc:
            logger.error("Ошибка detailed-транскрипции Qwen3-ASR: %s", exc)
            raise RuntimeError(f"Ошибка транскрипции Qwen3-ASR: {exc}") from exc
        return _payload(result, duration, word_timestamps, effective)

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        import mlx.core as mx
        from mlx_qwen3_asr.convert import quantize_model
        from mlx_qwen3_asr.load_models import load_model

        model, _config = load_model(self.qcfg.model_name, dtype=mx.float16)
        bits = self.qcfg.quantization_bits
        if bits is not None:
            quantize_model(
                model,
                bits=int(bits),
                group_size=int(self.qcfg.group_size),
            )
            logger.info(
                "Qwen3-ASR quantized in-process: model=%s bits=%s group_size=%s",
                self.qcfg.model_name,
                bits,
                self.qcfg.group_size,
            )
        self._model = model
        return model


def _as_float32(audio: np.ndarray) -> np.ndarray:
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)
    if audio.size == 0:
        return audio
    peak = max(abs(float(audio.max())), abs(float(audio.min())), 1e-9)
    if peak > 1.0:
        audio = audio / peak
    return audio


def _payload(
    result: Any,
    duration: float,
    word_timestamps: bool,
    effective_code: str | None,
) -> dict:
    text = (getattr(result, "text", None) or "").strip()
    chunks = list(getattr(result, "chunks", None) or [])
    words_raw = list(getattr(result, "segments", None) or []) if word_timestamps else []
    segments: list[dict] = []
    if chunks:
        last = len(chunks) - 1
        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                continue
            start = float(chunk.get("start") or 0.0)
            end = float(chunk.get("end") or 0.0)
            item: dict[str, Any] = {
                "id": index,
                "start": start,
                "end": end,
                "text": (chunk.get("text") or "").strip(),
            }
            if word_timestamps:
                item["words"] = _words_in_span(
                    words_raw, start, end, is_last=(index == last)
                )
            segments.append(item)
    elif text:
        item = {"id": 0, "start": 0.0, "end": float(duration), "text": text}
        if word_timestamps:
            item["words"] = [_word(w) for w in words_raw if isinstance(w, dict)]
        segments = [item]
    return {
        "text": text,
        "language": reported_language(getattr(result, "language", None), effective_code),
        "duration": float(duration),
        "segments": segments,
    }


def _word(raw: dict) -> dict:
    return {
        "word": raw.get("word") or raw.get("text") or "",
        "start": float(raw.get("start") or 0.0),
        "end": float(raw.get("end") or 0.0),
    }


def _words_in_span(words: list, start: float, end: float, *, is_last: bool) -> list[dict]:
    chosen = []
    for raw in words:
        if not isinstance(raw, dict):
            continue
        word_start = float(raw.get("start") or 0.0)
        if word_start < start:
            continue
        if is_last or word_start < end:
            chosen.append(_word(raw))
    return chosen
