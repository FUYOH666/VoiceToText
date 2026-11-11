"""/v1/audio/translations: speech → English via Whisper's translate task."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from model_catalog.registry import load_catalog
from stt_server import create_app
from tests.test_stt_server import _minimal_config, _mock_engine, _wav_bytes

STT = {
    "host": "127.0.0.1",
    "port": 8765,
    "max_upload_mb": 1,
    "request_timeout_seconds": 60,
    "preload_on_start": True,
    "idle_unload_seconds": 0,
}


def _client(engine_name: str, whisper_repo: str = "mlx-community/whisper-tiny-mlx"):
    config = _minimal_config(stt_server={**STT, "engine": engine_name})
    config.transcription.mlx_whisper.model_name = whisper_repo
    engine = _mock_engine("Hello, this is a test.")
    patches = [
        patch("stt_server.TranscriptionEngineWrapper", return_value=engine),
        patch("stt_server._warmup", return_value=None),
    ]
    for p in patches:
        p.start()
    client = TestClient(create_app(config))
    client.__enter__()
    return client, engine, patches


@pytest.fixture
def whisper_api():
    client, engine, patches = _client("mlx_whisper")
    yield client, engine
    client.__exit__(None, None, None)
    for p in patches:
        p.stop()


def _post(client, path="/v1/audio/translations", **data):
    return client.post(path, files={"file": ("a.wav", _wav_bytes(), "audio/wav")}, data=data)


def test_translation_uses_whisper_translate_task(whisper_api):
    client, engine = whisper_api
    r = _post(client)
    assert r.status_code == 200 and r.json()["text"] == "Hello, this is a test."
    assert engine.transcribe_detailed.call_args.kwargs["task"] == "translate"


def test_translation_verbose_json_reports_task(whisper_api):
    client, _ = whisper_api
    r = _post(client, response_format="verbose_json")
    assert r.json()["task"] == "translate"


def test_transcription_does_not_send_task(whisper_api):
    client, engine = whisper_api
    r = _post(client, path="/v1/audio/transcriptions")
    assert r.status_code == 200
    assert "task" not in engine.transcribe_detailed.call_args.kwargs


def test_qwen_cannot_translate():
    client, engine, patches = _client("qwen3_asr")
    try:
        r = _post(client)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "translation_unsupported"
        engine.transcribe_detailed.assert_not_called()
    finally:
        client.__exit__(None, None, None)
        for p in patches:
            p.stop()


@pytest.mark.parametrize(
    ("model_id", "ok"),
    [("whisper-large-v3", True), ("whisper-large-v3-8bit", True), ("whisper-large-v3-turbo-8bit", False)],
)
def test_catalog_flag_decides_for_known_whisper_models(model_id, ok):
    repo = load_catalog().get(model_id).repo
    client, _, patches = _client("mlx_whisper", whisper_repo=repo)
    try:
        r = _post(client)
        assert (r.status_code == 200) is ok
        if not ok:
            assert r.json()["error"]["code"] == "translation_unsupported"
            assert "large-v3" in r.json()["error"]["message"]
    finally:
        client.__exit__(None, None, None)
        for p in patches:
            p.stop()


def test_models_list_exposes_translates():
    catalog = {m.id: m for m in load_catalog().models}
    assert catalog["whisper-large-v3"].translates is True
    assert catalog["whisper-large-v3-turbo"].translates is False
    assert catalog["qwen3-asr-1.7b-8bit"].translates is False
