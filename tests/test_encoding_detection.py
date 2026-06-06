"""Тесты кодировок на статических фикстурах (PLAN §12.3, D8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from argos_translator.services.document_io import read_text_file, write_text_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "encodings"
RUSSIAN_TEXT = "Привет, мир! Это тест кодировки."


@pytest.mark.parametrize(
    ("filename", "expected_text"),
    [
        ("utf8.txt", RUSSIAN_TEXT),
        ("utf8_bom.txt", RUSSIAN_TEXT),
        ("cp1251.txt", RUSSIAN_TEXT),
        ("cp866.txt", RUSSIAN_TEXT),
        ("koi8r.txt", RUSSIAN_TEXT),
    ],
)
def test_fixture_encodings(filename: str, expected_text: str) -> None:
    path = FIXTURES / filename
    assert path.is_file(), f"missing fixture {path}"
    decoded = read_text_file(path)
    assert decoded.text == expected_text


def test_fixture_latin1() -> None:
    decoded = read_text_file(FIXTURES / "latin1.txt")
    assert "Cafe" in decoded.text


def test_fixture_empty() -> None:
    decoded = read_text_file(FIXTURES / "empty.txt")
    assert decoded.text == ""


def test_fixture_binary_garbage() -> None:
    decoded = read_text_file(FIXTURES / "garbage.bin")
    assert isinstance(decoded.text, str)


def test_fixture_save_roundtrip_cp1251(tmp_path: Path) -> None:
    src = FIXTURES / "cp1251.txt"
    decoded = read_text_file(src)
    out = tmp_path / "out.txt"
    write_text_file(out, decoded.text, decoded.encoding)
    assert out.read_bytes() == src.read_bytes()
