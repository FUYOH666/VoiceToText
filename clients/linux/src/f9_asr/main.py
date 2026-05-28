"""Main entry point for F9 ASR."""

import logging
import sys
from pathlib import Path

from f9_asr.config import Config
from f9_asr.hotkey_handler import HotkeyHandler

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    # Load configuration
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        config = Config.from_yaml(config_path)
        config.setup_logging()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Check ASR service availability
    from f9_asr.asr_client import ASRClient

    asr_client = ASRClient(config.asr)
    if not asr_client.health_check():
        logger.error(
            f"ASR service is not available at {config.asr.base_url}. "
            "Please ensure the service is running on port 8001."
        )
        sys.exit(1)

    # Start hotkey handler
    handler = HotkeyHandler(config)
    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        handler.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        handler.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
