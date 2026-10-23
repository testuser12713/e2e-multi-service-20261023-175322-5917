"""Unit tests for the text analyses."""

from __future__ import annotations

from worker.analyses import ANALYSES, reading_time, top_words, word_count


def test_word_count_ignores_punctuation() -> None:
    assert word_count("Hello, world! It's fine.") == {"words": 4}
    assert word_count("  ...  ") == {"words": 0}


def test_top_words_case_insensitive_and_punctuation() -> None:
    result = top_words("Apple apple, APPLE! banana; banana.")
    assert result == {"top_words": [{"word": "apple", "count": 3}, {"word": "banana", "count": 2}]}


def test_top_words_ties_alphabetical_and_max_five() -> None:
    result = top_words("g f e d c b a a")
    assert result["top_words"] == [
        {"word": "a", "count": 2},
        {"word": "b", "count": 1},
        {"word": "c", "count": 1},
        {"word": "d", "count": 1},
        {"word": "e", "count": 1},
    ]


def test_reading_time() -> None:
    assert reading_time("one two") == {"minutes": 0.1, "words": 2}
    r = reading_time(" ".join(["w"] * 300))
    assert r["words"] == 300
    assert abs(r["minutes"] - 1.5) < 1e-2


def test_registry() -> None:
    assert set(ANALYSES) == {"word_count", "top_words", "reading_time"}
