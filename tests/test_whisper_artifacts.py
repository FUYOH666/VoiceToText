"""Tests for Whisper tail artifact stripping."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "vtt2"))

from text.whisper_artifacts import strip_trailing_whisper_artifacts


class TestWhisperArtifacts:
    def test_strip_ru_tail_line(self):
        text = "Привет мир\nВЕСЕЛАЯ МУЗЫКА"
        cleaned, changed = strip_trailing_whisper_artifacts(
            text, languages=frozenset({"ru"})
        )
        assert changed
        assert cleaned == "Привет мир"

    def test_strip_en_suffix(self):
        text = "Hello world. Thank you for watching!"
        cleaned, changed = strip_trailing_whisper_artifacts(
            text, languages=frozenset({"en"})
        )
        assert changed
        assert "Thank you" not in cleaned

    def test_no_change_on_clean(self):
        text = "Обычная фраза без артефактов."
        cleaned, changed = strip_trailing_whisper_artifacts(
            text, languages=frozenset({"ru", "en"})
        )
        assert not changed
        assert cleaned == text
