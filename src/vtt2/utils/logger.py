"""
Logging setup for VTT2.
Format: ts level service msg meta
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

LOG_DIR = Path.home() / "Library" / "Logs" / "vtt2"
DEFAULT_LOG_FILE = LOG_DIR / "vtt2.log"


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application logging with console + rotating file output.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Log format (default: ts level name msg)
        log_file: Path to log file. None uses the default ~/Library/Logs/vtt2/vtt2.log.
                  Set to empty string "" to disable file logging entirely.

    Returns:
        Configured logger instance.
    """
    if format_string is None:
        format_string = "%(asctime)s %(levelname)s %(name)s %(message)s"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    # File logging with rotation (10 MB per file, 5 backups)
    if log_file != "":
        resolved = Path(log_file) if log_file else DEFAULT_LOG_FILE
        resolved.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                str(resolved),
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=numeric_level,
        format=format_string,
        handlers=handlers,
        force=True,
    )

    logger = logging.getLogger("vtt2")
    logger.info("Logging initialized (level: %s)", level)

    return logger
