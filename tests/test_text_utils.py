"""Тесты TextUtils."""

from __future__ import annotations

import pytest

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


def test_installed_from_codes() -> None:
    assert TextUtils.installed_from_codes(["en->ru", "ru->en"]) == {"en", "ru"}
    assert TextUtils.installed_from_codes(["en-ru"]) == {"en"}
    assert TextUtils.installed_from_codes(["en", "ru"]) == {"en", "ru"}


@pytest.mark.parametrize(
    ("detected", "cyrillic", "installed", "expected"),
    [
        ("nl", False, ["en->ru", "ru->en"], "en"),
        ("ca", False, ["en", "ru"], "en"),
        ("so", False, ["en->ru"], "en"),
        ("bg", True, ["en->ru", "ru->en"], "ru"),
        ("de", False, ["en->ru", "de->ru"], "de"),
        ("en", False, ["en->ru"], "en"),
        ("", False, ["en->ru"], "en"),
        ("auto", True, ["en->ru", "ru->en"], "ru"),
    ],
)
def test_snap_detected_lang_table(
    detected: str, cyrillic: bool, installed: list[str], expected: str
) -> None:
    assert (
        TextUtils.snap_detected_lang(
            detected,
            has_cyrillic=cyrillic,
            installed_from_codes=installed,
        )
        == expected
    )


class _FakeIso:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeLang:
    def __init__(self, code: str) -> None:
        self.iso_code_639_1 = _FakeIso(code)


class _FakeConf:
    def __init__(self, code: str, value: float) -> None:
        self.language = _FakeLang(code)
        self.value = value


class _FakeDetector:
    def __init__(self, code: str, confidence: float) -> None:
        self._code = code
        self._confidence = confidence

    def compute_language_confidence_values(self, text: str) -> list[_FakeConf]:
        return [_FakeConf(self._code, self._confidence)]


def _patch_lingua(monkeypatch: pytest.MonkeyPatch, lang: str, confidence: float) -> None:
    monkeypatch.setattr(
        "argos_translator.utils.text_utils._get_lingua_detector",
        lambda codes: _FakeDetector(lang, confidence),
    )


_LONG_EN = "This is a reasonably long English sentence used for language detection."
_LONG_RU = "Это достаточно длинный русский текст для проверки определения языка."


def test_detect_language_snaps_nl_even_with_high_conf(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lingua(monkeypatch, "nl", 0.99)
    assert TextUtils.detect_language(_LONG_EN, installed_from_codes={"en", "ru"}) == "en"


def test_detect_language_low_conf_uses_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lingua(monkeypatch, "nl", 0.40)
    assert TextUtils.detect_language(_LONG_EN, installed_from_codes={"en", "ru"}) == "en"


def test_detect_language_cyrillic_bg_snaps_to_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lingua(monkeypatch, "bg", 0.99)
    assert TextUtils.detect_language(_LONG_RU, installed_from_codes={"en", "ru"}) == "ru"


def test_detect_language_tiny_text_uses_heuristic() -> None:
    assert TextUtils.detect_language("Hi", installed_from_codes={"en", "ru"}) == "en"
    assert TextUtils.detect_language("Да", installed_from_codes={"en", "ru"}) == "ru"


def test_peek_words() -> None:
    from argos_translator.utils.detect_log import peek_words

    assert peek_words("") == ""
    assert peek_words("Hello world from Argos") == "Hello world from"
    assert peek_words("one") == "one"
    long = "x" * 40
    assert peek_words(f"{long} y z").startswith("x" * 24 + "…")


def test_detect_language_logs_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    from argos_translator.utils import detect_log as detect_log_mod

    lines: list[str] = []

    def _capture(msg: str, *args: object) -> None:
        lines.append(msg % args if args else msg)

    monkeypatch.setattr(detect_log_mod, "detect_info", _capture)
    monkeypatch.setattr(
        "argos_translator.utils.text_utils.detect_info",
        _capture,
    )
    TextUtils.detect_language("Hi", installed_from_codes={"en", "ru"})
    assert any("branch=tiny_text" in line for line in lines)
    assert any("peek=" in line for line in lines)


def test_resolve_auto_pair_table() -> None:
    assert TextUtils.resolve_auto_pair("ru", "ru") == ("ru", "en")
    assert TextUtils.resolve_auto_pair("en", "ru") == ("en", "ru")
    assert TextUtils.resolve_auto_pair("de", "ru") == ("de", "ru")
    assert TextUtils.resolve_auto_pair("de", "de") == ("de", "ru")
    assert TextUtils.resolve_auto_pair("", "ru") == ("en", "ru")
    assert TextUtils.resolve_auto_pair("en", "") == ("en", "ru")


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
