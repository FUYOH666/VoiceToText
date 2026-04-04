"""Тесты снятия хвостовых артефактов Whisper."""

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
