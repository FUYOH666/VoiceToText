"""
Снятие типичных хвостовых «галлюцинаций» Whisper перед вставкой текста.

Списки основаны на публичных наблюдениях (в т.ч. gist whisper-hallucinations-ru).

Два класса фраз:

* ``_*_SUFFIX_SAFE`` — титры и концовки видео («Субтитры сделал DimaTorzok»,
  «Thanks for watching!»). Их не говорят в обычной диктовке, поэтому они
  срезаются и как хвост строки после реального текста.
* ``_*_WHOLE_LINE`` — короткие и обычные слова («СМЕХ», «ПОЛИЦИЯ», «Thank you.»,
  «Поехали!»). Они бывают в настоящей речи, поэтому удаляются только если
  занимают всю последнюю строку (или весь сегмент) целиком.

Фильтр рассчитан только на модели семейства Whisper; для Qwen3-ASR и других
движков STT-сервер его не вызывает.
"""
from __future__ import annotations

from typing import FrozenSet

# RU: см. https://gist.github.com/waveletdeboshir/8bf52f04bf78018194f25b2390c08309
_RU_SUFFIX_SAFE: tuple[str, ...] = (
    "Спасибо за субтитры!",
    "Спасибо за субтитры Алексею Дубровскому!",
    "Субтитры добавил DimaTorzok",
    "Субтитры создавал DimaTorzok",
    "Субтитры сделал DimaTorzok",
    "Субтитры подогнал «Симон»!",
    "Редактор субтитров М.Лосева Корректор А.Егорова",
    "Редактор субтитров А.Синецкая Корректор А.Егорова",
    "Редактор субтитров Т.Горелова Корректор А.Егорова",
    "Редактор субтитров Е.Жукова Корректор А.Егорова",
    "Редактор субтитров А.Семкин Корректор А.Егорова",
    "Редактор субтитров А.Захарова Корректор А.Егорова",
    "ПОДПИШИСЬ НА КАНАЛ",
)

_RU_WHOLE_LINE: tuple[str, ...] = (
    "ВЕСЕЛАЯ МУЗЫКА",
    "СПОКОЙНАЯ МУЗЫКА",
    "ГРУСТНАЯ МЕЛОДИЯ",
    "ЛИРИЧЕСКАЯ МУЗЫКА",
    "ДИНАМИЧНАЯ МУЗЫКА",
    "ТАИНСТВЕННАЯ МУЗЫКА",
    "ТОРЖЕСТВЕННАЯ МУЗЫКА",
    "ИНТРИГУЮЩАЯ МУЗЫКА",
    "НАПРЯЖЕННАЯ МУЗЫКА",
    "ПЕЧАЛЬНАЯ МУЗЫКА",
    "ТРЕВОЖНАЯ МУЗЫКА",
    "МУЗЫКАЛЬНАЯ ЗАСТАВКА",
    "ПЕРЕСТРЕЛКА",
    "ГУДОК ПОЕЗДА",
    "РЁВ МОТОРА",
    "ШУМ ДВИГАТЕЛЯ",
    "СИГНАЛ АВТОМОБИЛЯ",
    "ЛАЙ СОБАК",
    "ПЕС ЛАЕТ",
    "КАШЕЛЬ",
    "ВЫСТРЕЛЫ",
    "ШУМ ДОЖДЯ",
    "ПЕСНЯ",
    "ПО ГРОМКОГОВОРИЧЕСКОМ ЯЗЫКЕ",
    "ПО ГРОМКОГОВОРИТЕЛЮ",
    "ВЗРЫВ",
    "ШУМ МОТОРА",
    "ПЛЕСК ВОДЫ",
    "ГУДОК АВТОМОБИЛЯ",
    "ЛАЙ СОБАКИ",
    "ПО ТВ.",
    "АПЛОДИСМЕНТЫ",
    "ГОРОДСКОЙ ШУМ",
    "ПОЛИЦИЯ",
    "ГОРОДСКОЙ ГУДОК",
    "СИГНАЛ МАШИНЫ",
    "СМЕХ",
    "СТУК В ДВЕРЬ",
    "ПОЛИЦЕЙСКАЯ СИРЕНА",
    "ЗВОНОК В ДВЕРЬ",
    "Смотрите продолжение во второй части видео.",
    "Смотрите продолжение в следующей части.",
    "Смотрите продолжение в следующей части видео.",
    "Смотрите продолжение в 4 части видео.",
    "Смотрите продолжение в следующей серии...",
    "Смотрите продолжение во второй части.",
    "Продолжение следует...",
    "Продолжение следует",
    "ПОДПИШИСЬ!",
    "ПОДПИШИСЬ",
    "Поехали!",
    "Поехали.",
    "Девушки отдыхают...",
    "🦜",
    "💥",
    "😎",
    "🤨",
    "🤔",
)

_EN_SUFFIX_SAFE: tuple[str, ...] = (
    "Thanks for watching!",
    "Thanks for watching",
    "Thank you for watching!",
    "Thank you for watching",
    "Please subscribe to my channel",
    "Subscribe to the channel",
    "Subscribe to my channel",
    "Subtitles by Amara.org",
    "Subtitles by the Amara.org community",
    "Don't forget to subscribe",
    "Like and subscribe",
    "Transcription by CastingWords",
)

_EN_WHOLE_LINE: tuple[str, ...] = (
    "Thank you.",
    "Thanks.",
    "Thanks!",
    "Please subscribe",
    "Subscribe",
    "To be continued",
    "To be continued...",
    "See you next time!",
    "See you next time",
    "Thank you for listening!",
    "Thank you for listening",
    "That's all!",
    "That's all",
)

# Обёртки, в которых Whisper печатает звуковые события: «(СМЕХ)», «[музыка]», «*кашель*».
_WRAPPER_CHARS = "()[]{}*«»\"'"


def _unique(phrases: list[str]) -> list[str]:
    return list({p.strip() for p in phrases if p.strip()})


def _collect(languages: FrozenSet[str]) -> tuple[list[str], list[str]]:
    """Returns (suffix_safe, whole_line_only) phrase lists for the given languages."""
    suffix: list[str] = []
    whole: list[str] = []
    if "ru" in languages:
        suffix.extend(_RU_SUFFIX_SAFE)
        whole.extend(_RU_WHOLE_LINE)
    if "en" in languages:
        suffix.extend(_EN_SUFFIX_SAFE)
        whole.extend(_EN_WHOLE_LINE)
    return _unique(suffix), _unique(whole)


def _normalize_line(line: str) -> str:
    return line.strip().strip(_WRAPPER_CHARS).strip().casefold()


def _boundary_ok_for_suffix(rest_raw: str) -> bool:
    if not rest_raw:
        return True
    c = rest_raw[-1]
    return c.isspace() or c in ".,;:!?…"


def strip_trailing_whisper_artifacts(
    text: str,
    *,
    languages: FrozenSet[str],
) -> tuple[str, bool]:
    """
    Удаляет известные хвостовые фразы Whisper.

    Последняя строка удаляется, если она целиком совпадает с любой фразой списка
    (без учёта регистра и скобок вокруг). Хвост внутри строки срезается только
    для фраз-титров (``*_SUFFIX_SAFE``), чтобы не терять настоящие слова вроде
    «...приехала полиция».

    Returns:
        (очищенный_текст, был_ли_хотя_бы_один_срез)
    """
    if not text or not text.strip() or not languages:
        return text, False

    suffix_phrases, whole_phrases = _collect(languages)
    if not suffix_phrases and not whole_phrases:
        return text, False

    whole_line_keys = {p.casefold() for p in (*suffix_phrases, *whole_phrases)}
    whole_line_keys |= {_normalize_line(p) for p in whole_line_keys}
    suffix_sorted = sorted(suffix_phrases, key=len, reverse=True)

    changed_any = False
    max_rounds = 80

    for _ in range(max_rounds):
        t = text.rstrip()
        if not t:
            text = ""
            changed_any = True
            break

        last_nl = t.rfind("\n")
        if last_nl == -1:
            prefix = ""
            last_line = t
        else:
            prefix = t[: last_nl + 1]
            last_line = t[last_nl + 1 :]

        if _normalize_line(last_line) in whole_line_keys:
            text = prefix.rstrip()
            changed_any = True
            continue

        progressed = False
        folded = t.casefold()
        for p in suffix_sorted:
            if len(t) < len(p) or not folded.endswith(p.casefold()):
                continue
            rest_raw = t[: len(t) - len(p)]
            if not _boundary_ok_for_suffix(rest_raw):
                continue
            text = rest_raw.rstrip()
            changed_any = True
            progressed = True
            break

        if not progressed:
            text = t
            break

    return text, changed_any
