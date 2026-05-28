"""Main entry point for F9 ASR."""

import argparse
import logging
import sys
from pathlib import Path

from f9_asr.config import Config
from f9_asr.hotkey_handler import HotkeyHandler

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="F9 ASR — Linux voice-to-text client")
    parser.add_argument(
        "--profile",
        default=None,
        help="Config profile: linux-f9-local, linux-f9-edge (or F9_PROFILE / VTT2_PROFILE)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check ASR connectivity and exit",
    )
    args = parser.parse_args()

    try:
        repo_root = Config.find_repo_root()
        config = Config.from_profile(profile=args.profile, repo_root=repo_root)
        config.setup_logging()
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        sys.exit(1)

    logger.info("F9 profile loaded: asr=%s", config.asr.base_url)

    from f9_asr.asr_client import ASRClient

    asr_client = ASRClient(config.asr)
    if not asr_client.health_check():
        logger.error(
            "ASR service is not available at %s. "
            "Set LOCAL_AI_ASR_BASE_URL in .env.local or use linux-f9-local profile.",
            config.asr.base_url,
        )
        sys.exit(1)

    if args.health:
        print(f"profile: {args.profile or 'from env/default'}")
        print(f"asr: {config.asr.base_url}")
        print("health: OK")
        return

    handler = HotkeyHandler(config)
    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        handler.stop()
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        handler.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
