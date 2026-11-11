"""Тесты снятия хвостовых артефактов Whisper."""

import pytest

from text.whisper_artifacts import strip_trailing_whisper_artifacts


def test_normal_text_unchanged():
    s = "Это обычный текст без артефактов."
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru", "en"}))
    assert out == s
    assert changed is False


def test_ru_tail_line_removed():
    s = "Диктовка про проект.\nСубтитры добавил DimaTorzok"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru"}))
    assert out == "Диктовка про проект."
    assert changed is True


def test_ru_dubrovsky_subtitles_tail_removed():
    s = "Текст диктовки.\nСпасибо за субтитры Алексею Дубровскому!"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru"}))
    assert out == "Текст диктовки."
    assert changed is True


def test_ru_dimatorzok_sozdaval_tail_removed():
    s = "Основной текст записи.\nСубтитры создавал DimaTorzok"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru"}))
    assert out == "Основной текст записи."
    assert changed is True


def test_ru_dimatorzok_sdelal_tail_removed():
    s = "Заметка.\nСубтитры сделал DimaTorzok"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru"}))
    assert out == "Заметка."
    assert changed is True


def test_multiple_trailing_lines_removed():
    s = "Основной текст\n\nПОДПИШИСЬ\nСубтитры добавил DimaTorzok"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru"}))
    assert out == "Основной текст"
    assert changed is True


def test_en_tail_suffix():
    s = "Meeting notes for today. Thanks for watching!"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"en"}))
    assert out == "Meeting notes for today."
    assert changed is True


def test_en_castingwords_tail_line():
    s = "Real spoken content.\nTranscription by CastingWords"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"en"}))
    assert out == "Real spoken content."
    assert changed is True


def test_en_thats_all_kept_inside_sentence():
    # "That's all!" is something people really say; only a whole line is removed.
    s = "Quick note here. That's all!"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"en"}))
    assert out == s
    assert changed is False


def test_en_thats_all_whole_line_removed():
    s = "Quick note here.\nThat's all!"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"en"}))
    assert out == "Quick note here."
    assert changed is True


@pytest.mark.parametrize(
    "text",
    [
        "К дому приехала полиция",
        "Это вызвало смех",
        "Сегодня у нас взрыв",
        "Мне понравилась эта песня",
        "Он сказал: Thank you.",
        "Ну что, поехали!",
        "Write it down. Thanks.",
        "Это была рабочая встреча. Продолжение следует",
    ],
)
def test_real_words_at_the_end_are_kept(text):
    out, changed = strip_trailing_whisper_artifacts(text, languages=frozenset({"ru", "en"}))
    assert out == text
    assert changed is False


@pytest.mark.parametrize(
    "line",
    ["СМЕХ", "(смех)", "[МУЗЫКАЛЬНАЯ ЗАСТАВКА]", "Thank you.", "Продолжение следует...", "ПОЛИЦИЯ"],
)
def test_sound_event_on_its_own_line_removed(line):
    s = f"Настоящий текст.\n{line}"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"ru", "en"}))
    assert out == "Настоящий текст."
    assert changed is True


def test_whole_text_artifact_becomes_empty():
    out, changed = strip_trailing_whisper_artifacts("Thank you.", languages=frozenset({"en"}))
    assert out == ""
    assert changed is True


def test_ru_phrase_not_stripped_when_only_en_list():
    s = "Текст\nСубтитры добавил DimaTorzok"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset({"en"}))
    assert out == s
    assert changed is False


def test_empty_languages_noop():
    s = "x\nSubscribe"
    out, changed = strip_trailing_whisper_artifacts(s, languages=frozenset())
    assert out == s
    assert changed is False
