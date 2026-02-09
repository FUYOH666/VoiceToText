"""ASR API client."""

import logging
from pathlib import Path
from typing import Optional

import requests

from f9_asr.config import ASRConfig

logger = logging.getLogger(__name__)


class ASRClient:
    """Client for ASR service API."""

    def __init__(self, config: ASRConfig):
        """Initialize ASR client."""
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.endpoint = config.transcription_endpoint

    def transcribe(self, audio_file: Path) -> str:
        """Transcribe audio file.

        Args:
            audio_file: Path to audio file

        Returns:
            Transcribed text

        Raises:
            requests.RequestException: If API request fails
            FileNotFoundError: If audio file doesn't exist
        """
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        url = f"{self.base_url}{self.endpoint}"
        logger.info(f"Transcribing {audio_file} via {url}")

        # Prepare multipart/form-data request
        # Use streaming to avoid loading entire file into memory
        with open(audio_file, "rb") as f:
            files = {"file": (audio_file.name, f, "audio/wav")}
            data = {
                "model": "whisper",  # Model name (ignored by service, for compatibility)
                "response_format": self.config.response_format,
            }

            # Add language if specified
            if self.config.language:
                data["language"] = self.config.language

            try:
                # Use streaming to avoid loading entire response into memory
                response = requests.post(
                    url,
                    files=files,
                    data=data,
                    timeout=self.config.timeout,
                    stream=True,  # Stream response to avoid loading all into memory
                )
                response.raise_for_status()

                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                # Read content only when needed (for text format)
                content_length = int(response.headers.get("Content-Length", 0))
                logger.debug(f"Response content length: {content_length}")

                # Handle different response formats
                # Read response content (streaming already enabled, but need to read for processing)
                if self.config.response_format == "text":
                    result = response.text.strip()
                elif self.config.response_format == "json":
                    try:
                        result_json = response.json()
                        logger.debug(f"Response JSON: {result_json}")
                        result = result_json.get("text", "")
                        # Check if result is empty but API returned success
                        if not result and result_json.get("language"):
                            logger.warning(
                                f"API returned empty text but detected language: {result_json.get('language')}"
                            )
                    except ValueError as e:
                        # Fallback: read text if JSON parsing fails
                        response_text = response.text[:200]  # Limit preview size
                        logger.warning(f"Failed to parse JSON response: {response_text}")
                        logger.debug(f"JSON parse error: {e}")
                        result = response.text.strip()
                else:
                    result = response.text.strip()

                # Clear response from memory after processing
                response.close()

                if not result:
                    logger.warning(
                        f"Empty transcription result. Response status: {response.status_code}, "
                        f"Content-Type: {response.headers.get('Content-Type')}, "
                        f"Content length: {content_length}"
                    )

                logger.info(f"Transcription successful: {len(result)} characters")
                return result

            except requests.exceptions.RequestException as e:
                logger.error(f"ASR API request failed: {e}")
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                raise

    def health_check(self) -> bool:
        """Check if ASR service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/healthz",
                timeout=5,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Health check failed: {e}")
            return False
