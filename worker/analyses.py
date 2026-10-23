"""Text analyses the worker runs on a job's text.

Each analysis takes the job text and returns the JSON-serializable result stored in
the job's ``result`` column:

- ``word_count``   -> ``{"words": int}``
- ``top_words``    -> ``{"top_words": [{"word": str, "count": int}, ...]}`` (at most 5)
- ``reading_time`` -> ``{"minutes": float, "words": int}`` (200 words per minute,
  one decimal)
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from typing import Any

WORDS_PER_MINUTE = 200
TOP_N = 5
_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def _words(text: str) -> list[str]:
    """Lower-cased words of ``text``; punctuation is ignored."""
    return _WORD_RE.findall(text.lower())


Analysis = Callable[[str], dict[str, Any]]


def word_count(text: str) -> dict[str, Any]:
    """Count the words of ``text``: ``{"words": int}``."""
    return {"words": len(_words(text))}


def top_words(text: str) -> dict[str, Any]:
    """The five most frequent words, case-insensitive, punctuation ignored, ties
    alphabetical: ``{"top_words": [{"word": str, "count": int}, ...]}``."""
    counts = Counter(_words(text))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]
    return {"top_words": [{"word": w, "count": c} for w, c in ranked]}


def reading_time(text: str) -> dict[str, Any]:
    """Reading time at 200 words per minute, one decimal:
    ``{"minutes": float, "words": int}``."""
    words = len(_words(text))
    if words == 0:
        return {"minutes": 0.0, "words": 0}
    minutes = max(0.1, round(words / WORDS_PER_MINUTE, 1))
    return {"minutes": minutes, "words": words}


ANALYSES: dict[str, Analysis] = {
    "word_count": word_count,
    "top_words": top_words,
    "reading_time": reading_time,
}
