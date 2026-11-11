"""Collapse Whisper repetition loops.

A stuck Whisper decode repeats one phrase or one segment many times in a row
("Я могу сказать, что это не так" x30). The decoder settings (temperature
fallback, no previous-text conditioning) prevent most loops; this is the
safety net for what still gets through.

Thresholds are deliberately high so real speech survives: "нет, нет, нет" or
"да, да, да, да" are left alone. A phrase of 3+ words must repeat 3+ times in a
row; a 1-2 word unit must repeat 6+ times.
"""
from __future__ import annotations

import re

_MAX_UNIT_WORDS = 25
_LONG_UNIT_MIN_REPEATS = 3   # units of 3+ words
_SHORT_UNIT_MIN_REPEATS = 6  # units of 1-2 words
_WORD = re.compile(r"\S+")
_EDGE_PUNCT = ".,;:!?…—–-\"'«»()[]"


def _norm(token: str) -> str:
    return token.strip(_EDGE_PUNCT).casefold().replace("ё", "е")


def _min_repeats(unit_len: int) -> int:
    return _LONG_UNIT_MIN_REPEATS if unit_len >= 3 else _SHORT_UNIT_MIN_REPEATS


def collapse_repeated_phrases(text: str) -> tuple[str, bool]:
    """Keep one copy of any word sequence that repeats too many times in a row.

    Returns (text, changed). Unchanged text is returned exactly as given.
    """
    if not text:
        return text, False
    spans = [(m.start(), m.end()) for m in _WORD.finditer(text)]
    words = [_norm(text[a:b]) for a, b in spans]
    n = len(words)
    if n < 6:
        return text, False

    keep: list[tuple[int, int]] = []  # [start, end) word index ranges to keep
    i = 0
    changed = False
    while i < n:
        collapsed = False
        # Shortest unit first, so a loop of phrase P is cut to one P (a unit of
        # two P's would also "repeat", leaving two copies).
        for unit in range(1, min(_MAX_UNIT_WORDS, (n - i) // 2) + 1):
            pattern = words[i : i + unit]
            if not any(pattern):
                continue
            repeats = 1
            while words[i + repeats * unit : i + (repeats + 1) * unit] == pattern:
                repeats += 1
            if repeats >= _min_repeats(unit):
                keep.append((i, i + unit))
                i += repeats * unit
                changed = True
                collapsed = True
                break
        if not collapsed:
            keep.append((i, i + 1))
            i += 1

    if not changed:
        return text, False

    # Rebuild from the original text so spacing and newlines survive; across a
    # collapsed run, use the whitespace that preceded the next kept word.
    out = [text[: spans[0][0]]]
    for idx, (start, end) in enumerate(keep):
        if idx:
            out.append(text[spans[start - 1][1] : spans[start][0]])
        out.append(text[spans[start][0] : spans[end - 1][1]])
    out.append(text[spans[-1][1] :])
    return "".join(out), True


def collapse_repeated_segments(segments: list[dict]) -> tuple[list[dict], bool]:
    """Merge runs of consecutive segments with the same text into one.

    The kept segment's ``end`` stretches over the run, so timecodes still cover
    the audio. A run of 3+ word segments collapses at 2 copies; shorter ones
    ("Да.") only at ``_SHORT_UNIT_MIN_REPEATS``.
    """
    if len(segments) < 2:
        return segments, False

    def key_of(seg: dict) -> str:
        return " ".join(_norm(w) for w in (seg.get("text") or "").split() if _norm(w))

    out: list[dict] = []
    changed = False
    i = 0
    while i < len(segments):
        key = key_of(segments[i])
        j = i + 1
        while key and j < len(segments) and key_of(segments[j]) == key:
            j += 1
        run = segments[i:j]
        limit = 2 if len(key.split()) >= 3 else _SHORT_UNIT_MIN_REPEATS
        if key and len(run) >= limit:
            # Keep the first copy (and its words); stretch it over the whole run.
            kept = dict(run[0])
            kept["end"] = max(float(s.get("end") or 0.0) for s in run)
            out.append(kept)
            changed = True
        else:
            out.extend(dict(s) for s in run)
        i = j
    return out, changed
