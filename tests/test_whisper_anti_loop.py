"""Whisper loop / hallucination guards: decoder options, silence trim, loop collapse."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from audio.silence import trim_silence
from text.repetition import collapse_repeated_phrases, collapse_repeated_segments

SR = 16000


def _tone(seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _hiss(seconds: float, amp: float = 0.001) -> np.ndarray:
    rng = np.random.default_rng(0)
    return (amp * rng.standard_normal(int(seconds * SR))).astype(np.float32)


# --- silence trim -----------------------------------------------------------


def test_trim_cuts_both_edges_and_reports_offset():
    audio = np.concatenate([_hiss(2.0), _tone(1.0), _hiss(3.0)])
    trimmed, offset = trim_silence(audio, SR)
    assert offset == pytest.approx(1.7, abs=0.05)  # 2.0 s minus 0.3 s padding
    assert len(trimmed) / SR == pytest.approx(1.6, abs=0.1)  # 1.0 s + 2 x 0.3 s


def test_trim_keeps_quiet_speech_tail():
    # A word that fades out 20 dB below the loud part must not be cut.
    audio = np.concatenate([_tone(1.0), _tone(0.5, amp=0.05), _hiss(2.0)])
    trimmed, offset = trim_silence(audio, SR)
    assert offset == 0.0
    assert len(trimmed) / SR >= 1.5


@pytest.mark.parametrize(
    "audio",
    [
        np.zeros(SR * 2, dtype=np.float32),  # digital silence
        _tone(2.0),  # nothing to trim
        np.zeros(100, dtype=np.float32),  # shorter than three frames
    ],
)
def test_trim_noop_cases(audio):
    trimmed, offset = trim_silence(audio, SR)
    assert offset == 0.0
    assert len(trimmed) == len(audio)


def test_trim_refuses_to_leave_a_sliver():
    # A lone click in 3 s of hiss would trim to ~0.6 s; leave it to Whisper.
    click = np.zeros(int(0.03 * SR), dtype=np.float32) + 0.5
    audio = np.concatenate([_hiss(1.5), click, _hiss(1.5)])
    audio[: int(0.03 * SR)] = audio[: int(0.03 * SR)]  # keep shape explicit
    trimmed, offset = trim_silence(audio, SR, pad_ms=100)
    assert offset == 0.0
    assert len(trimmed) == len(audio)


# --- phrase / segment loops ---------------------------------------------------


def test_long_phrase_loop_collapses_to_one_copy():
    loop = "Я могу сказать, что это не так, как вы думаете. " * 30
    text = f"Начало встречи. {loop}Конец."
    out, changed = collapse_repeated_phrases(text)
    assert changed is True
    assert out.count("Я могу сказать") == 1
    assert out.startswith("Начало встречи. Я могу сказать")
    assert out.endswith("Конец.")


@pytest.mark.parametrize(
    "text",
    [
        "Нет, нет, нет, я так не думаю.",
        "Да, да, да, да, да, конечно.",  # 5 short repeats: real speech
        "Обычная диктовка без повторов, просто текст про проект и задачи.",
        "Раз два три, раз два три, и всё.",  # 3-word unit only twice
    ],
)
def test_real_repetition_is_kept(text):
    out, changed = collapse_repeated_phrases(text)
    assert changed is False
    assert out == text


def test_six_short_repeats_collapse():
    out, changed = collapse_repeated_phrases("ага ага ага ага ага ага ага понял")
    assert changed is True
    assert out == "ага понял"


def test_whitespace_and_newlines_survive_outside_the_loop():
    text = "Строка один.\nА дальше петля петля петля петля петля петля петля\nКонец."
    out, changed = collapse_repeated_phrases(text)
    assert changed is True
    assert out == "Строка один.\nА дальше петля\nКонец."


def test_identical_long_segments_merge_and_span_time():
    seg = "Продолжение следует в следующей серии"
    segments = [{"id": 0, "start": 0.0, "end": 2.0, "text": "Реальный текст."}] + [
        {"id": i, "start": 2.0 * i, "end": 2.0 * (i + 1), "text": seg} for i in range(1, 6)
    ]
    out, changed = collapse_repeated_segments(segments)
    assert changed is True
    assert [s["text"] for s in out] == ["Реальный текст.", seg]
    assert out[1]["start"] == 2.0 and out[1]["end"] == 12.0


def test_short_identical_segments_kept():
    segments = [
        {"id": 0, "start": 0.0, "end": 1.0, "text": "Да."},
        {"id": 1, "start": 1.0, "end": 2.0, "text": "Да."},
    ]
    out, changed = collapse_repeated_segments(segments)
    assert changed is False
    assert len(out) == 2


# --- decoder options and wiring ------------------------------------------------


def _transcriber(**overrides):
    from config.loader import MLXWhisperConfig
    from transcription.mlx_engine import MLXWhisperTranscriber

    t = MLXWhisperTranscriber.__new__(MLXWhisperTranscriber)
    t.mlx_config = MLXWhisperConfig(model_name="mlx-community/whisper-tiny", **overrides)
    t.config = SimpleNamespace(transcription=SimpleNamespace(mlx_whisper=t.mlx_config))
    t.sample_rate = SR
    t._model_cache = None
    t._transcription_count = 0
    t._resolved_model_source = None
    return t


def test_default_decode_options_enable_fallback_and_drop_conditioning():
    opts = _transcriber()._decode_options()
    assert opts["temperature"] == (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    assert opts["condition_on_previous_text"] is False
    assert opts["logprob_threshold"] == -1.0
    assert "hallucination_silence_threshold" not in opts


def test_silence_threshold_only_with_word_timestamps():
    opts = _transcriber()._decode_options(word_timestamps=True)
    assert opts["hallucination_silence_threshold"] == 2.0


def test_fallback_can_be_disabled():
    opts = _transcriber(temperature_fallback=False)._decode_options()
    assert opts["temperature"] == 0.0


def test_transcribe_detailed_trims_and_shifts_timecodes(monkeypatch):
    from transcription import mlx_engine

    seen = {}

    def fake_transcribe(audio, **kwargs):
        seen["len"] = len(audio)
        seen["kwargs"] = kwargs
        return {
            "text": " Привет",
            "language": "ru",
            "segments": [{"id": 0, "start": 0.3, "end": 1.2, "text": " Привет"}],
        }

    monkeypatch.setattr(mlx_engine.whisper, "transcribe", fake_transcribe)
    monkeypatch.setattr("transcription.hf_cache.resolve_cached_snapshot", lambda name: name)
    audio = np.concatenate([_hiss(2.0), _tone(1.0), _hiss(3.0)])
    payload = _transcriber().transcribe_detailed(audio, language="ru")

    assert seen["len"] < len(audio)
    assert seen["kwargs"]["condition_on_previous_text"] is False
    assert isinstance(seen["kwargs"]["temperature"], tuple)
    # 1.7 s were cut from the start; timecodes are back on the upload's timeline.
    assert payload["segments"][0]["start"] == pytest.approx(2.0, abs=0.05)
    assert payload["duration"] == pytest.approx(6.0, abs=0.01)


def test_transcribe_detailed_collapses_loop(monkeypatch):
    from transcription import mlx_engine

    loop_seg = "Я могу сказать, что это не так"
    result = {
        "text": " ".join([loop_seg] * 4),
        "language": "ru",
        "segments": [
            {"id": i, "start": float(i), "end": float(i + 1), "text": loop_seg} for i in range(4)
        ],
    }
    monkeypatch.setattr(mlx_engine.whisper, "transcribe", lambda audio, **kw: result)
    monkeypatch.setattr("transcription.hf_cache.resolve_cached_snapshot", lambda name: name)
    payload = _transcriber(trim_silence=False).transcribe_detailed(_tone(4.0), language="ru")
    assert payload["text"] == loop_seg
    assert len(payload["segments"]) == 1
    assert payload["segments"][0]["end"] == 4.0
