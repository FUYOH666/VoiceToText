"""Audio upload decoding: every failure is AudioDecodeError (HTTP 400)."""
from __future__ import annotations

import io

import numpy as np
import pytest
import soundfile as sf

from audio import decode
from audio.decode import AudioDecodeError, decode_audio_bytes


def _wav(seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    audio = np.zeros(int(seconds * sample_rate), dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    return buf.getvalue()


def test_wav_decodes_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(decode, "_find_ffmpeg", lambda: None)
    audio = decode_audio_bytes(_wav(), filename="a.wav", sample_rate=16000)
    assert audio.dtype == np.float32
    assert len(audio) == 1600


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [("voice.m4a", "audio/mp4"), ("bad.wav", "audio/wav"), ("blob", None)],
)
def test_garbage_raises_decode_error_without_ffmpeg(monkeypatch, filename, content_type):
    monkeypatch.setattr(decode, "_find_ffmpeg", lambda: None)
    with pytest.raises(AudioDecodeError):
        decode_audio_bytes(b"not audio at all", filename=filename, content_type=content_type)


def test_empty_upload_is_decode_error():
    with pytest.raises(AudioDecodeError):
        decode_audio_bytes(b"", filename="a.wav")


def test_find_ffmpeg_falls_back_to_homebrew_path(monkeypatch, tmp_path):
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setattr(decode.shutil, "which", lambda name: None)
    monkeypatch.setattr(decode, "_FFMPEG_FALLBACK_PATHS", ("/nonexistent/ffmpeg", str(fake)))
    assert decode._find_ffmpeg() == str(fake)


def test_find_ffmpeg_none_when_absent(monkeypatch):
    monkeypatch.setattr(decode.shutil, "which", lambda name: None)
    monkeypatch.setattr(decode, "_FFMPEG_FALLBACK_PATHS", ("/nonexistent/ffmpeg",))
    assert decode._find_ffmpeg() is None
