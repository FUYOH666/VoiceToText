"""Mock ASR server tests (CI-safe, no Tailscale)."""
from pytest_httpserver import HTTPServer

from vtt_asr_client.client import ASRClient, ASRClientConfig


def test_asr_client_healthz_and_transcribe():
    with HTTPServer() as server:
        server.expect_request(
            "/v1/audio/transcriptions", method="POST"
        ).respond_with_json({"text": "hi"})
        server.expect_request("/healthz", method="GET").respond_with_data("ok")

        base = server.url_for("/").rstrip("/")
        cfg = ASRClientConfig(base_url=base, timeout=5)
        client = ASRClient(cfg)

        assert client.healthz()
        assert client.transcribe_bytes(b"RIFF", filename="a.wav") == "hi"
