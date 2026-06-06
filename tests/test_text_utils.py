"""Тесты TextUtils."""

from __future__ import annotations

from argos_translator.utils.text_utils import TextUtils


def test_split_into_paragraphs() -> None:
    text = "First para.\n\nSecond para.\n\nThird."
    paras = TextUtils.split_into_paragraphs(text)
    assert len(paras) == 3
    assert paras[0] == "First para."


def test_detect_language_russian() -> None:
    assert TextUtils.detect_language("Привет мир") == "ru"


def test_detect_language_english() -> None:
    assert TextUtils.detect_language("Hello world") == "en"


def test_make_sentence_chunks_single() -> None:
    sentences = ["Short.", "Also short."]
    chunks = TextUtils.make_sentence_chunks(sentences, max_chars=4000)
    assert chunks == [(0, 2)]


def test_make_sentence_chunks_overlap() -> None:
    sentences = [f"Sentence {i}." for i in range(20)]
    chunks = TextUtils.make_sentence_chunks(sentences, max_chars=80, overlap=2)
    assert len(chunks) > 1
    first_end = chunks[0][1]
    second_start = chunks[1][0]
    assert second_start <= first_end


def test_build_argos_units() -> None:
    text = "Hello world.\n\nSecond paragraph here."
    units = TextUtils.build_argos_units(text)
    assert len(units) >= 1
    assert all(len(u) == 3 and isinstance(u[0], str) and isinstance(u[1], int) and isinstance(u[2], bool) for u in units)


def test_code_fence_preserved_when_disabled() -> None:
    text = "# Title\n\nSome prose.\n\n```python\nprint('x')\n```\n\nMore prose."
    units = TextUtils.build_argos_units(text, translate_code_blocks=False)
    code_units = [u for u in units if not u[2]]
    assert len(code_units) == 1
    assert "```python" in code_units[0][0]
    assert "print('x')" in code_units[0][0]
    translatable = [u for u in units if u[2]]
    assert any("Some prose" in u[0] for u in translatable)
    assert any("More prose" in u[0] for u in translatable)


def test_split_prose_and_code_fences() -> None:
    text = "A\n\n```\ncode\n```\n\nB"
    segments = TextUtils.split_prose_and_code_fences(text)
    assert len(segments) == 3
    assert segments[0][1] is True
    assert segments[1][1] is False
    assert "```" in segments[1][0]
