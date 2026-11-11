"""Trim leading and trailing silence before Whisper.

Whisper invents text on silence ("Продолжение следует...", "Thanks for
watching!"), and a dictation usually ends with a second or two of silence
before the hotkey is pressed again. Cutting those edges removes the most
common source of tail hallucinations without a VAD model.

The level is relative to the loudest frame, because the server peak-normalizes
audio before it gets here, so absolute dBFS says nothing about speech.
"""
from __future__ import annotations

import numpy as np

FRAME_MS = 30
# Frames this far below the loudest frame count as silence. Speech, including
# quiet consonants next to vowels, sits well within 30 dB of the loudest frame.
THRESHOLD_DB = -30.0
# Kept around the first and last voiced frame so word onsets and fades survive.
PAD_MS = 300
# Never return less than this; a shorter result means the clip was mostly
# silence and Whisper's own no-speech logic should decide.
MIN_KEEP_S = 0.5


def trim_silence(
    audio: np.ndarray,
    sample_rate: int,
    *,
    threshold_db: float = THRESHOLD_DB,
    pad_ms: int = PAD_MS,
) -> tuple[np.ndarray, float]:
    """Return (trimmed audio, seconds cut from the start).

    The offset lets callers shift segment and word timestamps back onto the
    original timeline. Audio that is too short, flat or would shrink below
    ``MIN_KEEP_S`` is returned unchanged with offset 0.
    """
    frame = max(1, int(sample_rate * FRAME_MS / 1000))
    total = len(audio)
    frames = total // frame
    if frames < 3:
        return audio, 0.0

    blocks = np.asarray(audio[: frames * frame], dtype=np.float32).reshape(frames, frame)
    rms = np.sqrt(np.mean(blocks * blocks, axis=1))
    loudest = float(rms.max())
    if loudest <= 1e-6:
        return audio, 0.0

    level_db = 20.0 * np.log10(np.maximum(rms, 1e-10) / loudest)
    voiced = np.flatnonzero(level_db > threshold_db)
    if voiced.size == 0:
        return audio, 0.0

    pad = int(round(pad_ms / FRAME_MS))
    first = max(int(voiced[0]) - pad, 0)
    last = min(int(voiced[-1]) + pad + 1, frames)
    start = first * frame
    end = total if last >= frames else last * frame

    if start == 0 and end == total:
        return audio, 0.0
    if (end - start) < MIN_KEEP_S * sample_rate:
        return audio, 0.0
    return audio[start:end], start / float(sample_rate)
