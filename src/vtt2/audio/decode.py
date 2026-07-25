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


def _decode_with_ffmpeg(data: bytes, sample_rate: int, suffix: str) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioDecodeError(
            f"Формат {suffix or 'unknown'} требует ffmpeg, но ffmpeg не найден в PATH"
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

        import soundfile as sf

        audio, sr = sf.read(str(dst), dtype="float32", always_2d=False)
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

    if prefer_ffmpeg:
        try:
            return _decode_with_ffmpeg(data, sample_rate, suffix or ".ogg")
        except AudioDecodeError:
            # fall through to soundfile once
            pass

    try:
        audio = _decode_with_soundfile(data, sample_rate)
    except Exception as e:
        if prefer_ffmpeg:
            raise
        logger.debug("soundfile decode failed (%s), trying ffmpeg", e)
        try:
            return _decode_with_ffmpeg(data, sample_rate, suffix or ".wav")
        except AudioDecodeError:
            raise AudioDecodeError(f"Не удалось декодировать аудио: {e}") from e

    if len(audio) == 0:
        raise AudioDecodeError("Аудио не содержит сэмплов")
    return audio
