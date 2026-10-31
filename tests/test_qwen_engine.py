"""Qwen3-ASR engine: mocked library, no weight download."""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest
from config.loader import Config, STTServerConfig
from stt_server import _configured_model_name, _profile_language, run_server
from transcription.engine import TranscriptionEngineWrapper
from transcription.qwen_engine import (
    Qwen3ASRTranscriber,
    library_language_name,
    reported_language,
)


def _config(*, bits=8, language="ru"):
    qcfg = SimpleNamespace(
        model_name="Qwen/Qwen3-ASR-1.7B",
        quantization_bits=bits,
        group_size=64,
        language=language,
    )
    return SimpleNamespace(transcription=SimpleNamespace(qwen3_asr=qcfg, engine="qwen3_asr"))


def _result():
    return SimpleNamespace(
        text="hello world",
        language="English",
        chunks=[
            {"text": "hello", "start": 0.0, "end": 1.0, "chunk_index": 0, "language": "English"},
            {"text": "world", "start": 1.0, "end": 2.0, "chunk_index": 1, "language": "English"},
        ],
        segments=[
            {"text": "hello", "start": 0.2, "end": 0.5},
            {"text": "world", "start": 1.2, "end": 1.6},
        ],
    )


def _install_fake_qwen(monkeypatch):
    calls = {"transcribe": [], "quantize": [], "load": []}
    sentinel = object()

    pkg = types.ModuleType("mlx_qwen3_asr")

    def transcribe(audio, **kwargs):
        calls["transcribe"].append(kwargs)
        return _result()

    pkg.transcribe = transcribe

    convert = types.ModuleType("mlx_qwen3_asr.convert")

    def quantize_model(model, bits=4, group_size=64, encoder_bits=None):
        calls["quantize"].append((model, bits, group_size))
        return model

    convert.quantize_model = quantize_model

    load_models = types.ModuleType("mlx_qwen3_asr.load_models")

    def load_model(name, dtype=None):
        calls["load"].append((name, dtype))
        return sentinel, object()

    load_models.load_model = load_model
    load_models._ModelHolder = type("H", (), {"clear": staticmethod(lambda: None)})

    tok = types.ModuleType("mlx_qwen3_asr.tokenizer")
    known = {"ru", "en", "russian", "english"}
    names = {"ru": "Russian", "en": "English", "russian": "Russian", "english": "English"}
    tok.language_is_known = lambda value: str(value).lower() in known
    tok.canonicalize_language = lambda value: names.get(str(value).lower(), value)
    tok._TokenizerHolder = type("T", (), {"clear": staticmethod(lambda: None)})

    monkeypatch.setitem(sys.modules, "mlx_qwen3_asr", pkg)
    monkeypatch.setitem(sys.modules, "mlx_qwen3_asr.convert", convert)
    monkeypatch.setitem(sys.modules, "mlx_qwen3_asr.load_models", load_models)
    monkeypatch.setitem(sys.modules, "mlx_qwen3_asr.tokenizer", tok)
    return calls, sentinel


class TestQwenExtraMissing:
    def test_engine_raises_without_fallback(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "mlx_qwen3_asr", None)
        with pytest.raises(RuntimeError, match="uv sync --extra qwen"):
            TranscriptionEngineWrapper(_config())

    def test_run_server_exits_before_bind(self, monkeypatch, project_root):
        cfg = Config.from_yaml(str(project_root / "config.qwen.yaml"), project_root)

        def boom():
            raise RuntimeError(
                "mlx-qwen3-asr is not installed. "
                "Install the optional extra: uv sync --extra qwen"
            )

        monkeypatch.setattr("transcription.qwen_engine.ensure_qwen_installed", boom)
        with pytest.raises(SystemExit, match="uv sync --extra qwen"):
            run_server(cfg)


class TestQwenTranscribeDetailed:
    def test_chunks_language_and_quantization(self, monkeypatch):
        calls, sentinel = _install_fake_qwen(monkeypatch)
        engine = Qwen3ASRTranscriber(_config())
        audio = np.zeros(16000, dtype=np.float32)
        payload = engine.transcribe_detailed(
            audio,
            word_timestamps=False,
            language="en",
            requested_language="en",
            initial_prompt="names",
        )
        assert payload["text"] == "hello world"
        assert payload["language"] == "en"
        assert "words" not in payload["segments"][0]
        assert payload["segments"][0]["text"] == "hello"
        assert payload["segments"][1]["start"] == 1.0
        kwargs = calls["transcribe"][0]
        assert kwargs["language"] == "English"
        assert kwargs["return_timestamps"] is False
        assert kwargs["return_chunks"] is True
        assert kwargs["context"] == "names"
        assert kwargs["model"] is sentinel
        assert calls["load"][0][0] == "Qwen/Qwen3-ASR-1.7B"
        assert calls["quantize"] == [(sentinel, 8, 64)]

    def test_words_only_when_requested(self, monkeypatch):
        calls, _sentinel = _install_fake_qwen(monkeypatch)
        engine = Qwen3ASRTranscriber(_config())
        audio = np.zeros(32000, dtype=np.float32)
        payload = engine.transcribe_detailed(
            audio, word_timestamps=True, language="ru", requested_language="ru"
        )
        assert calls["transcribe"][0]["language"] == "Russian"
        assert calls["transcribe"][0]["return_timestamps"] is True
        assert payload["language"] == "ru"
        assert payload["segments"][0]["words"][0]["word"] == "hello"
        assert payload["segments"][1]["words"][0]["word"] == "world"

    def test_auto_is_library_autodetect(self, monkeypatch):
        calls, _sentinel = _install_fake_qwen(monkeypatch)
        engine = Qwen3ASRTranscriber(_config())
        audio = np.zeros(1600, dtype=np.float32)
        payload = engine.transcribe_detailed(
            audio, language=None, requested_language="auto"
        )
        assert calls["transcribe"][0]["language"] is None
        assert payload["language"] == "en"

    def test_blank_config_language_is_not_a_surprise(self, monkeypatch):
        calls, _sentinel = _install_fake_qwen(monkeypatch)
        engine = Qwen3ASRTranscriber(_config(language="ru"))
        audio = np.zeros(1600, dtype=np.float32)
        engine.transcribe_detailed(audio, requested_language="omitted")
        assert calls["transcribe"][0]["language"] == "Russian"

    def test_float16_skips_quantize(self, monkeypatch):
        calls, _sentinel = _install_fake_qwen(monkeypatch)
        engine = Qwen3ASRTranscriber(_config(bits=None))
        audio = np.zeros(1600, dtype=np.float32)
        engine.transcribe(audio)
        assert calls["quantize"] == []
        assert calls["transcribe"][0]["context"] == ""


class TestQwenLanguageMap:
    def test_iso_and_thai(self, monkeypatch):
        _install_fake_qwen(monkeypatch)
        assert library_language_name(None) is None
        assert library_language_name("auto") is None
        assert library_language_name("ru") == "Russian"
        assert library_language_name("th") == "Thai"
        assert reported_language("English", "en") == "en"
        assert reported_language("English", None) == "en"
        assert reported_language("unknown", None) is None


class TestQwenProfile:
    def test_yaml_keeps_menubar_on_http(self, project_root):
        cfg = Config.from_yaml(str(project_root / "config.qwen.yaml"), project_root)
        assert cfg.stt_server.engine == "qwen3_asr"
        assert cfg.transcription.engine == "local_stt"
        assert cfg.transcription.qwen3_asr is not None
        assert cfg.transcription.qwen3_asr.model_name == "moona3k/mlx-qwen3-asr-1.7b-8bit"
        assert cfg.transcription.qwen3_asr.quantization_bits is None
        assert cfg.transcription.qwen3_asr.group_size == 64
        assert cfg.transcription.qwen3_asr.language == "ru"
        assert cfg.transcription.mlx_whisper.model_name == "mlx-community/whisper-large-v3-mlx"
        assert _profile_language(cfg) == "ru"
        assert _configured_model_name(cfg) == "moona3k/mlx-qwen3-asr-1.7b-8bit"

    def test_default_profile_is_qwen(self, project_root):
        cfg = Config.from_yaml(str(project_root / "config.yaml"), project_root)
        assert cfg.stt_server.engine == "qwen3_asr"
        assert cfg.transcription.engine == "local_stt"
        assert _profile_language(cfg) == "ru"
        assert _configured_model_name(cfg) == "moona3k/mlx-qwen3-asr-1.7b-8bit"

    def test_unknown_engine_rejected(self):
        with pytest.raises(Exception):
            STTServerConfig(engine="parakeet")
