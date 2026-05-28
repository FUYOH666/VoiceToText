"""Shared OpenAI-compatible ASR HTTP client for Mac VTT2 and Linux F9."""
from vtt_asr_client.client import ASRClient, ASRClientConfig, transcribe_wav_bytes

__all__ = ["ASRClient", "ASRClientConfig", "transcribe_wav_bytes"]
