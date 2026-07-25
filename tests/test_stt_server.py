"""Tests for local STT HTTP API (mocked engine — no MLX load)."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from config.loader import Config
from stt_server import create_app, state


def _minimal_config(**overrides) -> Config:
    data = {
        "app": {"version": "1.3.0", "name": "VTTv2"},
        "transcription": {
            "engine": "local_stt",
            "local_stt": {
                "base_url": "http://127.0.0.1:8765",
                "path": "/v1/audio/transcriptions",
                "timeout_seconds": 60,
            },
            "mlx_whisper": {
                "model_name": "mlx-community/whisper-tiny-mlx",
                "language": "ru",
            },
        },
        "audio": {"sample_rate": 16000, "channels": 1},
        "ui": {"auto_paste_enabled": True, "hotkey": "option+space"},
        "menu_bar": {
            "icon_idle": "🎤",
            "icon_recording": "🔴",
            "show_status": True,
        },
        "text_processing": {
            "enabled": False,
            "strip_whisper_tail_artifacts": True,
            "whisper_artifact_languages": ["ru", "en"],
        },
        "performance": {
            "use_neural_engine": True,
            "max_concurrent_tasks": 1,
            "memory_limit_mb": 4096,
        },
        "logging": {"level": "INFO"},
        "stt_server": {
            "host": "127.0.0.1",
            "port": 8765,
            "max_upload_mb": 1,
            "request_timeout_seconds": 60,
            "engine": "mlx_whisper",
        },
    }
    data.update(overrides)
    return Config(**data)


def _wav_bytes(seconds: float = 0.2, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    return buf.getvalue()


@pytest.fixture
def mock_ready_app():
    """App with mocked TranscriptionEngineWrapper that marks ready."""
    config = _minimal_config()
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "привет мир"

    with patch("stt_server.TranscriptionEngineWrapper", return_value=mock_engine):
        with patch("stt_server._warmup", return_value=None):
            app = create_app(config)
            with TestClient(app) as client:
                yield client, mock_engine


class TestSTTServerAPI:
    def test_healthz_always_ok(self, mock_ready_app):
        client, _ = mock_ready_app
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_readyz_200_when_ready(self, mock_ready_app):
        client, _ = mock_ready_app
        r = client.get("/readyz")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

    def test_transcriptions_happy_path(self, mock_ready_app):
        client, mock_engine = mock_ready_app
        r = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("a.wav", _wav_bytes(), "audio/wav")},
        )
        assert r.status_code == 200
        assert r.json()["text"] == "привет мир"
        mock_engine.transcribe.assert_called()

    def test_transcriptions_413_too_large(self, mock_ready_app):
        client, _ = mock_ready_app
        huge = b"RIFF" + b"x" * (2 * 1024 * 1024)
        r = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("big.bin", huge, "application/octet-stream")},
        )
        assert r.status_code == 413

    def test_transcriptions_400_empty(self, mock_ready_app):
        client, _ = mock_ready_app
        r = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("empty.wav", b"", "audio/wav")},
        )
        assert r.status_code == 400

    def test_transcriptions_400_invalid_audio(self, mock_ready_app):
        client, _ = mock_ready_app
        r = client.post(
            "/v1/audio/transcriptions",
            files={"file": ("bad.wav", b"not-audio", "audio/wav")},
        )
        assert r.status_code == 400

    def test_readyz_503_before_ready(self):
        config = _minimal_config()

        def boom(*_a, **_k):
            raise RuntimeError("mlx missing")

        with patch("stt_server.TranscriptionEngineWrapper", side_effect=boom):
            app = create_app(config)
            with TestClient(app) as client:
                r = client.get("/readyz")
                assert r.status_code == 503
                assert r.json()["status"] == "not_ready"
                tr = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": ("a.wav", _wav_bytes(), "audio/wav")},
                )
                assert tr.status_code == 503


class TestLocalSTTClient:
    def test_transcribe_calls_http(self):
        from transcription.local_stt import LocalSTTTranscriber

        config = _minimal_config()
        audio = np.zeros(1600, dtype=np.float32)

        class FakeResp:
            def __init__(self, code, payload=None, text=""):
                self.status_code = code
                self._payload = payload or {}
                self.text = text

            def json(self):
                return self._payload

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception(f"http {self.status_code}")

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, url):
                assert url.endswith("/readyz")
                return FakeResp(200, {"status": "ready"})

            def post(self, url, files=None):
                assert "/v1/audio/transcriptions" in url
                return FakeResp(200, {"text": "ok from stt"})

        with patch("transcription.local_stt.httpx.Client", FakeClient):
            t = LocalSTTTranscriber(config)
            assert t.transcribe(audio) == "ok from stt"

    def test_not_ready_raises(self):
        from transcription.local_stt import LocalSTTTranscriber

        config = _minimal_config()
        audio = np.zeros(1600, dtype=np.float32)

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, url):
                class R:
                    status_code = 503
                    text = '{"status":"not_ready"}'

                return R()

        with patch("transcription.local_stt.httpx.Client", FakeClient):
            t = LocalSTTTranscriber(config)
            with pytest.raises(RuntimeError, match="не готов"):
                t.transcribe(audio)


class TestSTTServerConfig:
    def test_reject_non_loopback_host(self):
        with pytest.raises(Exception):
            _minimal_config(
                stt_server={
                    "host": "0.0.0.0",
                    "port": 8765,
                    "max_upload_mb": 25,
                    "request_timeout_seconds": 600,
                    "engine": "mlx_whisper",
                }
            )

    def test_default_config_yaml_loads(self, project_root):
        cfg = Config.from_yaml(str(project_root / "config.yaml"), project_root)
        assert cfg.app.version == "1.3.0"
        assert cfg.transcription.engine == "local_stt"
        assert cfg.stt_server.port == 8765
        assert cfg.stt_server.host == "127.0.0.1"
