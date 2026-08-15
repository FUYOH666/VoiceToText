"""CLI --health for local_stt (HTTP healthz, no rumps)."""
from unittest.mock import MagicMock, patch

import yaml

from main import health_check_command


def _write_local_stt_config(path):
    data = {
        "app": {"version": "1.4.0", "name": "VTTv2"},
        "transcription": {
            "engine": "local_stt",
            "local_stt": {
                "base_url": "http://127.0.0.1:8765",
                "path": "/v1/audio/transcriptions",
                "timeout_seconds": 60,
                "warmup_wait_seconds": 30,
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
            "preload_on_start": False,
            "idle_unload_seconds": 900,
        },
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


def test_health_check_local_stt_ok(tmp_path):
    cfg = tmp_path / "config.yaml"
    _write_local_stt_config(cfg)
    resp = MagicMock(status_code=200)
    with patch("httpx.get", return_value=resp) as get:
        assert health_check_command(str(cfg)) == 0
        get.assert_called_once()
        assert get.call_args[0][0].endswith("/healthz")


def test_health_check_local_stt_down(tmp_path):
    cfg = tmp_path / "config.yaml"
    _write_local_stt_config(cfg)
    with patch("httpx.get", side_effect=ConnectionError("refused")):
        assert health_check_command(str(cfg)) == 0
