"""
Decode uploaded audio bytes → float32 mono PCM at target sample rate.
Uses soundfile when possible; ffmpeg for ogg/webm/m4a/opus.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Extensions that typically need ffmpeg (libsndfile may lack codecs)
_FFMPEG_SUFFIXES = {".ogg", ".oga", ".opus", ".webm", ".m4a", ".mp3", ".mp4", ".aac"}

# Checked when ffmpeg is not on PATH (Apple Silicon and Intel Homebrew).
_FFMPEG_FALLBACK_PATHS = ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg")


class AudioDecodeError(ValueError):
    """Invalid or unsupported audio input."""


def _to_mono_float32(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    return audio.astype(np.float32, copy=False)


def _resample_linear(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or len(audio) == 0:
        return audio
    duration = len(audio) / float(src_rate)
    dst_len = max(1, int(round(duration * dst_rate)))
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _decode_with_soundfile(data: bytes, sample_rate: int) -> np.ndarray:
    import io

    import soundfile as sf

    with sf.SoundFile(io.BytesIO(data)) as f:
        audio = f.read(dtype="float32", always_2d=False)
        src_rate = int(f.samplerate)
    audio = _to_mono_float32(np.asarray(audio))
    return _resample_linear(audio, src_rate, sample_rate)


def _find_ffmpeg() -> str | None:
    """ffmpeg from PATH, or from the usual Homebrew prefixes.

    launchd starts the STT agent with a minimal PATH (/usr/bin:/bin:...), so a
    Homebrew ffmpeg is invisible to ``shutil.which`` there.
    """
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in _FFMPEG_FALLBACK_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def _decode_with_ffmpeg(data: bytes, sample_rate: int, suffix: str) -> np.ndarray:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise AudioDecodeError(
            f"Формат {suffix or 'unknown'} требует ffmpeg, но ffmpeg не найден "
            "(установите: brew install ffmpeg)"
        )

    suffix = suffix if suffix.startswith(".") else f".{suffix}" if suffix else ".bin"
    with tempfile.TemporaryDirectory(prefix="vtt2-stt-") as tmp:
        src = Path(tmp) / f"input{suffix}"
        dst = Path(tmp) / "out.wav"
        src.write_bytes(data)
        cmd = [
            ffmpeg,
            "-nostdin",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "wav",
            str(dst),
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or b"").decode("utf-8", errors="replace")[-500:]
            raise AudioDecodeError(f"ffmpeg не смог декодировать аудио: {err}") from e
        except subprocess.TimeoutExpired as e:
            raise AudioDecodeError("ffmpeg: таймаут декодирования") from e
        except OSError as e:
            raise AudioDecodeError(f"ffmpeg не запустился: {e}") from e

        import soundfile as sf

        try:
            audio, sr = sf.read(str(dst), dtype="float32", always_2d=False)
        except Exception as e:
            raise AudioDecodeError(f"ffmpeg вернул нечитаемый WAV: {e}") from e
        audio = _to_mono_float32(np.asarray(audio))
        return _resample_linear(audio, int(sr), sample_rate)


def decode_audio_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    sample_rate: int = 16000,
) -> np.ndarray:
    """
    Decode audio file bytes to float32 mono at sample_rate.

    Raises:
        AudioDecodeError: empty, unsupported, or decode failure
    """
    if not data:
        raise AudioDecodeError("Пустой файл")

    suffix = Path(filename or "").suffix.lower()
    ct = (content_type or "").lower()

    prefer_ffmpeg = suffix in _FFMPEG_SUFFIXES or any(
        x in ct for x in ("ogg", "opus", "webm", "mp4", "m4a", "mpeg", "mp3")
    )

    # Every failure below must surface as AudioDecodeError (HTTP 400), never as a
    # raw libsndfile/OS error (HTTP 500).
    errors: list[str] = []
    if prefer_ffmpeg:
        try:
            return _non_empty(_decode_with_ffmpeg(data, sample_rate, suffix or ".ogg"))
        except AudioDecodeError as e:
            errors.append(str(e))

    try:
        audio = _decode_with_soundfile(data, sample_rate)
    except Exception as e:
        errors.append(f"soundfile: {e}")
        if prefer_ffmpeg:
            raise AudioDecodeError(_failure_message(errors)) from e
        logger.debug("soundfile decode failed (%s), trying ffmpeg", e)
        try:
            audio = _decode_with_ffmpeg(data, sample_rate, suffix or ".wav")
        except AudioDecodeError as e2:
            errors.append(str(e2))
            raise AudioDecodeError(_failure_message(errors)) from e

    return _non_empty(audio)


def _non_empty(audio: np.ndarray) -> np.ndarray:
    if len(audio) == 0:
        raise AudioDecodeError("Аудио не содержит сэмплов")
    return audio


def _failure_message(errors: list[str]) -> str:
    return "Не удалось декодировать аудио: " + "; ".join(errors)
