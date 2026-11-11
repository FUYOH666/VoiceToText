"""Model catalog, memory tiers, user overlay and the /v1/models API (no real downloads)."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from config.loader import Config
from model_catalog import registry
from model_catalog.registry import (
    ModelSpec,
    add_user_model,
    config_with,
    load_catalog,
    write_selection,
)
from server.models_api import detect_family
from stt_server import create_app, state
from tests.test_stt_server import _minimal_config, _mock_engine, _wav_bytes

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --- catalog -------------------------------------------------------------------


def test_shipped_catalog_is_valid():
    catalog = load_catalog()
    ids = [m.id for m in catalog.models]
    assert len(ids) == len(set(ids))
    assert {m.family for m in catalog.models} <= {"qwen3_asr", "mlx_whisper"}
    for m in catalog.models:
        assert "/" in m.repo and m.download_gb > 0 and m.ram_gb > 0
        assert m.verified_revision and len(m.verified_revision) == 40
    # Quantized options exist for low-memory Macs.
    assert any(m.quantization in ("8bit", "4bit") and m.ram_gb < 1.5 for m in catalog.models)
    # Qwen entries must be mlx-qwen3-asr checkpoints (moona3k), not mlx-community/mlx-audio ones.
    assert all(m.repo.startswith("moona3k/") for m in catalog.models if m.family == "qwen3_asr")


@pytest.mark.parametrize(
    ("memory_gb", "expected"),
    [(8, "qwen3-asr-0.6b-8bit"), (16, "qwen3-asr-1.7b-8bit"), (64, "qwen3-asr-1.7b-8bit")],
)
def test_recommendation_by_memory(memory_gb, expected):
    assert load_catalog().recommended(memory_gb) == expected


def test_user_models_are_added_but_never_shadow_shipped(tmp_path):
    user_file = tmp_path / "models.yaml"
    custom = ModelSpec(id="custom-tiny", title="tiny", family="mlx_whisper", repo="me/tiny-mlx")
    shadow = ModelSpec(id="whisper-small", title="evil", family="mlx_whisper", repo="evil/small")
    add_user_model(custom, user_file)
    add_user_model(shadow, user_file)
    catalog = load_catalog(user_path=user_file)
    assert catalog.get("custom-tiny").custom is True
    assert catalog.get("whisper-small").repo == "mlx-community/whisper-small-mlx"


def test_broken_user_models_file_is_ignored(tmp_path):
    user_file = tmp_path / "models.yaml"
    user_file.write_text("models: [{id: x, family: nope, title: t, repo: a/b}]", encoding="utf-8")
    assert load_catalog(user_path=user_file).get("x") is None


@pytest.mark.parametrize(
    ("config", "files", "family"),
    [
        ({"n_mels": 128, "n_audio_ctx": 1500}, ["config.json", "weights.npz"], "mlx_whisper"),
        ({"model_type": "qwen3_asr"}, ["config.json", "model.safetensors"], "qwen3_asr"),
        ({"architectures": ["Qwen3ASRForConditionalGeneration"]}, ["model.safetensors"], "qwen3_asr"),
        ({"model_type": "whisper"}, ["config.json", "pytorch_model.bin"], None),  # HF torch format
        ({"model_type": "llama"}, ["model.safetensors"], None),
    ],
)
def test_detect_family(config, files, family):
    assert detect_family(config, files) == family


# --- user overlay ----------------------------------------------------------------


def test_selection_overlay_beats_repo_config_but_not_env(monkeypatch):
    spec = load_catalog().get("whisper-large-v3-turbo-8bit")
    path = write_selection(spec)
    assert path.parent == Path(registry.user_dir())
    cfg = Config.from_yaml(str(PROJECT_ROOT / "config.yaml"), PROJECT_ROOT)
    assert cfg.stt_server.engine == "mlx_whisper"
    assert cfg.transcription.mlx_whisper.model_name == spec.repo

    monkeypatch.setenv("VTT2_STT_SERVER_ENGINE", "qwen3_asr")
    cfg = Config.from_yaml(str(PROJECT_ROOT / "config.yaml"), PROJECT_ROOT)
    assert cfg.stt_server.engine == "qwen3_asr"


def test_write_selection_keeps_other_user_keys():
    path = registry.user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stt_server:\n  idle_unload_seconds: 60\n", encoding="utf-8")
    write_selection(load_catalog().get("qwen3-asr-0.6b-8bit"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["stt_server"] == {"idle_unload_seconds": 60, "engine": "qwen3_asr"}
    assert data["transcription"]["qwen3_asr"]["quantization_bits"] is None


def test_config_with_selects_family_and_repo():
    base = _minimal_config()
    spec = load_catalog().get("qwen3-asr-0.6b-8bit")
    cfg = config_with(base, spec)
    assert cfg.stt_server.engine == "qwen3_asr"
    assert cfg.transcription.qwen3_asr.model_name == spec.repo
    assert cfg.transcription.qwen3_asr.quantization_bits is None
    assert base.stt_server.engine == "mlx_whisper"  # input untouched


# --- API -----------------------------------------------------------------------


@pytest.fixture
def api():
    """Running app with a mocked engine; installed = turbo-8bit and qwen 0.6B only."""
    installed = {"mlx-community/whisper-large-v3-turbo-8bit", "moona3k/mlx-qwen3-asr-0.6b-8bit"}
    engine = _mock_engine("привет")
    built: list[Config] = []

    def make_engine(cfg):
        built.append(cfg)
        return engine

    fake_installed = lambda spec: spec.repo in installed  # noqa: E731
    with patch("stt_server.TranscriptionEngineWrapper", side_effect=make_engine), patch(
        "stt_server._warmup", return_value=None
    ), patch("model_catalog.registry.is_installed", side_effect=fake_installed), patch(
        "server.models_api.is_installed", side_effect=fake_installed
    ), patch("server.models_api.system_memory_gb", return_value=16.0):
        with TestClient(create_app(_minimal_config())) as client:
            yield client, built, installed


def test_list_models_marks_installed_recommended_and_configured(api):
    client, _, _ = api
    body = client.get("/v1/models").json()
    by_id = {m["id"]: m for m in body["data"]}
    assert body["system_memory_gb"] == 16.0
    assert body["recommended"] == "qwen3-asr-1.7b-8bit"
    assert by_id["whisper-large-v3-turbo-8bit"]["installed"] is True
    assert by_id["whisper-large-v3"]["installed"] is False
    assert by_id["whisper-large-v3"]["fits_memory"] is True
    # The test config loads a repo that is not in the catalog.
    assert body["active"] == "configured" and by_id["configured"]["active"] is True


def test_activate_unknown_and_not_installed(api):
    client, _, _ = api
    r = client.post("/v1/models/nope/activate")
    assert r.status_code == 404 and r.json()["error"]["code"] == "model_not_found"
    r = client.post("/v1/models/whisper-large-v3/activate")
    assert r.status_code == 409 and r.json()["error"]["code"] == "model_not_installed"
    assert not registry.user_config_path().exists()


def test_activate_switches_model_and_persists(api):
    client, built, _ = api
    r = client.post("/v1/models/qwen3-asr-0.6b-8bit/activate")
    assert r.status_code == 200 and r.json() == {"active": "qwen3-asr-0.6b-8bit", "changed": True}
    assert built[-1].stt_server.engine == "qwen3_asr"
    assert state.config.transcription.qwen3_asr.model_name == "moona3k/mlx-qwen3-asr-0.6b-8bit"
    assert client.get("/healthz").json()["model"] == "moona3k/mlx-qwen3-asr-0.6b-8bit"
    saved = yaml.safe_load(registry.user_config_path().read_text(encoding="utf-8"))
    assert saved["stt_server"]["engine"] == "qwen3_asr"
    # Transcription still works on the new model.
    r = client.post("/v1/audio/transcriptions", files={"file": ("a.wav", _wav_bytes(), "audio/wav")})
    assert r.status_code == 200 and r.json()["text"] == "привет"
    assert client.get("/v1/models").json()["active"] == "qwen3-asr-0.6b-8bit"
    # Activating the active model again is a no-op.
    assert client.post("/v1/models/qwen3-asr-0.6b-8bit/activate").json()["changed"] is False


def test_failed_activation_keeps_previous_model(api):
    client, _, _ = api
    before = state.config.stt_server.engine
    with patch("stt_server.TranscriptionEngineWrapper", side_effect=RuntimeError("bad weights")):
        r = client.post("/v1/models/qwen3-asr-0.6b-8bit/activate")
    assert r.status_code == 500 and r.json()["error"]["code"] == "model_load_failed"
    assert state.config.stt_server.engine == before
    assert not registry.user_config_path().exists()


def test_delete_refuses_active_model(api):
    client, _, _ = api
    client.post("/v1/models/whisper-large-v3-turbo-8bit/activate")
    r = client.delete("/v1/models/whisper-large-v3-turbo-8bit")
    assert r.status_code == 409 and r.json()["error"]["code"] == "model_active"
    with patch("server.models_api._delete_from_cache", return_value=123) as deleter:
        r = client.delete("/v1/models/qwen3-asr-0.6b-8bit")
    assert r.status_code == 200 and r.json()["freed_bytes"] == 123
    deleter.assert_called_once_with("moona3k/mlx-qwen3-asr-0.6b-8bit")


def test_download_runs_in_background_and_reports_done(api):
    client, _, installed = api
    calls = []

    def fake_download(**kwargs):
        calls.append(kwargs)
        installed.add(kwargs["repo_id"])

    with patch("model_catalog.downloads.snapshot_download", side_effect=fake_download), patch(
        "model_catalog.downloads.hub_total_bytes", return_value=1000
    ), patch("model_catalog.downloads.is_installed", side_effect=lambda s: s.repo in installed):
        r = client.post("/v1/models/whisper-small/download")
        assert r.status_code == 202
        for _ in range(100):
            status = client.get("/v1/models/whisper-small/download").json()
            if status["state"] == "done":
                break
            time.sleep(0.02)
    assert status["state"] == "done" and status["progress"] == 1.0
    assert calls[0]["repo_id"] == "mlx-community/whisper-small-mlx"
    assert "*.npz" in calls[0]["allow_patterns"]


def test_custom_model_is_validated_and_listed(api):
    client, _, _ = api
    assert client.post("/v1/models/custom", json={"repo": "not a repo"}).status_code == 400
    spec = ModelSpec(
        id="custom-whisper-tiny-mlx", title="whisper-tiny-mlx", family="mlx_whisper",
        repo="mlx-community/whisper-tiny-mlx", download_gb=0.07, ram_gb=0.4, min_memory_gb=8, custom=True,
    )
    with patch("server.models_api.inspect_repo", return_value=spec):
        r = client.post("/v1/models/custom", json={"repo": "mlx-community/whisper-tiny-mlx"})
    assert r.status_code == 200 and r.json()["id"] == "custom-whisper-tiny-mlx"
    ids = [m["id"] for m in client.get("/v1/models").json()["data"]]
    assert "custom-whisper-tiny-mlx" in ids
