"""Hotkey handler for F9 key."""

import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from pynput import keyboard

from f9_asr.asr_client import ASRClient
from f9_asr.audio_recorder import AudioRecorder
from f9_asr.config import Config

logger = logging.getLogger(__name__)


class HotkeyHandler:
    """Handler for F9 hotkey to toggle recording."""

    def __init__(self, config: Config):
        """Initialize hotkey handler."""
        self.config = config
        self.recorder = AudioRecorder(config.audio)
        self.asr_client = ASRClient(config.asr)
        self.is_recording = False
        self.listener: Optional[keyboard.Listener] = None

    def _on_press(self, key: keyboard.Key) -> None:
        """Handle key press event."""
        try:
            # Check if F9 is pressed
            if key == keyboard.Key.f9:
                self._toggle_recording()
        except AttributeError:
            # Handle special keys
            pass

    def _toggle_recording(self) -> None:
        """Toggle recording state."""
        if self.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start recording."""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return

        logger.info("Starting recording...")
        self.is_recording = True

        # Write PID file
        pid_file = Path(self.config.hotkey.pid_file)
        pid_file.write_text(str(os.getpid()))

        try:
            self.recorder.start_recording()
            self._show_notification("Recording started", "Speak now...")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            self._show_notification("Error", f"Failed to start recording: {e}", error=True)

    def _stop_and_transcribe(self) -> None:
        """Stop recording and transcribe."""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return

        logger.info("Stopping recording and transcribing...")
        self.is_recording = False

        # Remove PID file
        pid_file = Path(self.config.hotkey.pid_file)
        if pid_file.exists():
            pid_file.unlink()

        try:
            # Stop recording
            audio_file = self.recorder.stop_recording()
            if not audio_file:
                logger.warning("No audio file recorded")
                self._show_notification("Error", "No audio recorded", error=True)
                return

            # Check service health
            if not self.asr_client.health_check():
                logger.error("ASR service is not available")
                self._show_notification(
                    "Error",
                    "ASR service is not available. Check if service is running on port 8001.",
                    error=True,
                )
                self.recorder.cleanup()
                return

            # Transcribe
            self._show_notification("Transcribing", "Processing audio...")
            try:
                text = self.asr_client.transcribe(audio_file)
            except Exception as e:
                logger.error(f"Transcription failed: {e}", exc_info=True)
                self._show_notification("Error", f"Transcription failed: {str(e)[:50]}", error=True)
                self.recorder.cleanup()
                return

            if text and text.strip():
                logger.info(f"Transcription: {text}")
                # Limit notification text to avoid memory issues
                notification_text = text[:100] + ("..." if len(text) > 100 else "")
                self._show_notification("Transcription", notification_text)

                # Copy to clipboard if enabled
                if self.config.ui.copy_to_clipboard:
                    self._copy_to_clipboard(text)

                # Clear text from memory after copying
                del text
                del notification_text

                # Cleanup
                self.recorder.cleanup()
            else:
                logger.warning(f"Empty transcription result. Audio file: {audio_file}, size: {audio_file.stat().st_size} bytes")
                self._show_notification(
                    "Warning",
                    "No text transcribed. Check microphone and try speaking louder.",
                    error=True,
                )
                # Keep file for debugging (but limit to last 5 debug files)
                debug_file = audio_file.parent / f"debug_{audio_file.name}"
                try:
                    import shutil
                    shutil.copy2(audio_file, debug_file)
                    logger.info(f"Saved debug file: {debug_file}")
                    
                    # Clean up old debug files (keep only last 5)
                    debug_files = sorted(
                        audio_file.parent.glob("debug_*.wav"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    for old_debug in debug_files[5:]:  # Keep only last 5
                        try:
                            old_debug.unlink()
                            logger.debug(f"Removed old debug file: {old_debug}")
                        except Exception as e:
                            logger.debug(f"Failed to remove old debug file: {e}")
                except Exception as e:
                    logger.debug(f"Failed to save debug file: {e}")
                self.recorder.cleanup()

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            self._show_notification("Error", f"Transcription failed: {e}", error=True)
            self.recorder.cleanup()

    def _show_notification(self, title: str, message: str, error: bool = False) -> None:
        """Show desktop notification."""
        if not self.config.ui.show_notifications:
            return

        try:
            import subprocess

            urgency = "critical" if error else "normal"
            subprocess.run(
                [
                    "notify-send",
                    "-u", urgency,
                    "-t", "3000",
                    title,
                    message,
                ],
                check=False,
                timeout=1,
            )
        except Exception as e:
            logger.debug(f"Failed to show notification: {e}")

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard using xclip."""
        import subprocess

        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            process.communicate(input=text.encode("utf-8"))
            if process.returncode == 0:
                logger.info("Text copied to clipboard")
            else:
                raise subprocess.CalledProcessError(process.returncode, "xclip")
        except FileNotFoundError:
            logger.warning("xclip not found. Please install: sudo apt install xclip")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to copy to clipboard: {e}")

    def start(self) -> None:
        """Start listening for hotkey."""
        logger.info(f"Starting hotkey listener for {self.config.hotkey.key.upper()}...")

        # Clean up old files on startup
        if self.config.audio.cleanup_max_age_hours > 0:
            logger.info(
                f"Cleaning up old temporary files (older than {self.config.audio.cleanup_max_age_hours} hours)..."
            )
            self.recorder.cleanup_old_files(max_age_hours=self.config.audio.cleanup_max_age_hours)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start keyboard listener
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

        logger.info("Hotkey listener started. Press F9 to start/stop recording.")
        logger.info("Press Ctrl+C to exit.")

        # Keep the main thread alive
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop listening for hotkey."""
        logger.info("Stopping hotkey listener...")

        # Stop recording if in progress
        if self.is_recording:
            self._stop_and_transcribe()

        # Stop listener
        if self.listener:
            self.listener.stop()

        # Cleanup
        self.recorder.cleanup()

        # Remove PID file
        pid_file = Path(self.config.hotkey.pid_file)
        if pid_file.exists():
            pid_file.unlink()

        logger.info("Hotkey listener stopped")

    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
