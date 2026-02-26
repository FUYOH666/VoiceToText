"""Audio recording module using arecord."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from f9_asr.config import AudioConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Audio recorder using arecord."""

    def __init__(self, config: AudioConfig):
        """Initialize audio recorder."""
        self.config = config
        self.recording_process: Optional[subprocess.Popen] = None
        self.temp_file: Optional[Path] = None

        # Ensure temp directory exists
        Path(config.temp_dir).mkdir(parents=True, exist_ok=True)

    def start_recording(self) -> Path:
        """Start audio recording.

        Returns:
            Path to the temporary audio file

        Raises:
            RuntimeError: If recording fails to start
        """
        if self.recording_process is not None:
            logger.warning("Recording already in progress")
            return self.temp_file

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            dir=self.config.temp_dir,
            delete=False,
        )
        self.temp_file = Path(temp_file.name)
        temp_file.close()

        logger.info(f"Starting recording to {self.temp_file}")

        # Build arecord command
        cmd = ["arecord", "-f", self.config.format, "-r", str(self.config.sample_rate)]
        device = getattr(self.config, "device", None)
        if device:
            cmd.extend(["-D", device])
            logger.debug(f"Using ALSA device: {device}")
        cmd.extend(["-c", str(self.config.channels), str(self.temp_file)])

        try:
            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.info("Recording started")
            return self.temp_file
        except FileNotFoundError:
            raise RuntimeError(
                "arecord not found. Please install alsa-utils: sudo apt install alsa-utils"
            )
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise RuntimeError(f"Failed to start recording: {e}")

    def stop_recording(self) -> Optional[Path]:
        """Stop audio recording.

        Returns:
            Path to the recorded audio file, or None if recording was not in progress
        """
        if self.recording_process is None:
            logger.warning("No recording in progress")
            return None

        logger.info("Stopping recording...")

        # Terminate recording process
        try:
            self.recording_process.terminate()
            stdout, stderr = self.recording_process.communicate(timeout=2)
            if stderr:
                logger.debug(f"arecord stderr: {stderr.decode()}")
        except subprocess.TimeoutExpired:
            logger.warning("Recording process did not terminate, killing...")
            self.recording_process.kill()
            self.recording_process.communicate()
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")

        self.recording_process = None

        # Check if file exists and has content
        if self.temp_file and self.temp_file.exists():
            file_size = self.temp_file.stat().st_size
            if file_size > 0:
                logger.info(f"Recording stopped. File size: {file_size} bytes")
                return self.temp_file
            else:
                logger.warning("Recording file is empty")
                self.temp_file.unlink()
                self.temp_file = None
                return None
        else:
            logger.warning("Recording file not found")
            self.temp_file = None
            return None

    def is_recording(self) -> bool:
        """Check if recording is in progress."""
        if self.recording_process is None:
            return False
        return self.recording_process.poll() is None

    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_file and self.temp_file.exists():
            try:
                self.temp_file.unlink()
                logger.debug(f"Cleaned up {self.temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {self.temp_file}: {e}")
            self.temp_file = None

    def cleanup_old_files(self, max_age_hours: int = 24) -> None:
        """Clean up old temporary files in temp directory.

        Args:
            max_age_hours: Maximum age of files in hours before deletion (default: 24)
        """
        import time

        temp_dir = Path(self.config.temp_dir)
        if not temp_dir.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        total_size = 0

        try:
            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            total_size += file_size
                            logger.debug(f"Deleted old file: {file_path} (age: {file_age/3600:.1f}h)")
                    except Exception as e:
                        logger.warning(f"Failed to delete old file {file_path}: {e}")

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old files ({total_size / 1024 / 1024:.2f} MB)"
                )
        except Exception as e:
            logger.warning(f"Failed to cleanup old files: {e}")
