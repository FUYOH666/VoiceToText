"""
Снятие типичных хвостовых «галлюцинаций» Whisper перед вставкой текста.

Списки основаны на публичных наблюдениях (в т.ч. gist whisper-hallucinations-ru).
Удаляется только хвост (последняя строка или суффикс с безопасной границей).
"""
from __future__ import annotations

from typing import FrozenSet

# RU: см. https://gist.github.com/waveletdeboshir/8bf52f04bf78018194f25b2390c08309
_RU_PHRASES: tuple[str, ...] = (
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
    "Смотрите продолжение во второй части видео.",
    "Смотрите продолжение в следующей части.",
    "Смотрите продолжение в следующей части видео.",
    "Смотрите продолжение в 4 части видео.",
    "Смотрите продолжение в следующей серии...",
    "Смотрите продолжение во второй части.",
    "Продолжение следует...",
    "Продолжение следует",
    "ПОДПИШИСЬ НА КАНАЛ",
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

_EN_PHRASES: tuple[str, ...] = (
    "Thanks for watching!",
    "Thanks for watching",
    "Thank you for watching!",
    "Thank you for watching",
    "Thank you.",
    "Thanks.",
    "Please subscribe",
    "Please subscribe to my channel",
    "Subscribe to the channel",
    "Subscribe to my channel",
    "Subscribe",
    "Subtitles by Amara.org",
    "Subtitles by the Amara.org community",
    "To be continued",
    "To be continued...",
    "See you next time!",
    "See you next time",
    "Don't forget to subscribe",
    "Like and subscribe",
)


def _collect_phrases(languages: FrozenSet[str]) -> list[str]:
    out: list[str] = []
    if "ru" in languages:
        out.extend(_RU_PHRASES)
    if "en" in languages:
        out.extend(_EN_PHRASES)
    # Уникальные, порядок длины задаём отдельно
    return list({p.strip() for p in out if p.strip()})


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
    Удаляет известные хвостовые фразы Whisper (последняя строка целиком или суффикс).

    Returns:
        (очищенный_текст, был_ли_хотя_бы_один_срез)
    """
    if not text or not text.strip() or not languages:
        return text, False

    phrases_sorted = sorted(_collect_phrases(languages), key=len, reverse=True)
    if not phrases_sorted:
        return text, False

    changed_any = False
    max_rounds = 80

    for _ in range(max_rounds):
        t = text.rstrip()
        if not t:
            text = ""
            changed_any = True
            break

        progressed = False

        # Пустые строки в конце
        while t.endswith("\n"):
            t = t[:-1].rstrip()
            progressed = True
            changed_any = True

        if not t:
            text = ""
            break

        last_nl = t.rfind("\n")
        if last_nl == -1:
            prefix = ""
            last_line = t.strip()
        else:
            prefix = t[: last_nl + 1]
            last_line = t[last_nl + 1 :].strip()

        for p in phrases_sorted:
            if last_line.casefold() == p.casefold():
                text = prefix.rstrip()
                changed_any = True
                progressed = True
                break

        if progressed:
            continue

        for p in phrases_sorted:
            pl, tl = len(p), len(t)
            if tl < pl:
                continue
            if not t.casefold().endswith(p.casefold()):
                continue
            rest_raw = t[: tl - pl]
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
