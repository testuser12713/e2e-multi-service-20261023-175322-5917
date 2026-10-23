"""Text analyses the worker runs on a job's text.

Each analysis takes the job text and returns the JSON-serializable result stored in
the job's ``result`` column:

- ``word_count``   -> ``{"words": int}``
- ``top_words``    -> ``{"top_words": [{"word": str, "count": int}, ...]}`` (at most 5)
- ``reading_time`` -> ``{"minutes": float, "words": int}`` (200 words per minute,
  one decimal)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Analysis = Callable[[str], dict[str, Any]]


def word_count(text: str) -> dict[str, Any]:
    """Count the words of ``text``: ``{"words": int}``."""
    return {}


def top_words(text: str) -> dict[str, Any]:
    """The five most frequent words, case-insensitive, punctuation ignored, ties
    alphabetical: ``{"top_words": [{"word": str, "count": int}, ...]}``."""
    return {}


def reading_time(text: str) -> dict[str, Any]:
    """Reading time at 200 words per minute, one decimal:
    ``{"minutes": float, "words": int}``."""
    return {}


ANALYSES: dict[str, Analysis] = {
    "word_count": word_count,
    "top_words": top_words,
    "reading_time": reading_time,
}
