"""Тесты автоопределения кодировки (D8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from argos_translator.services.document_io import (
    detect_encoding,
    read_text_file,
    resolve_output_encoding,
    suggest_output_path,
    write_text_file,
)

RUSSIAN_TEXT = "Привет, мир! Это тест кодировки."


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    d = tmp_path / "encodings"
    d.mkdir()
    return d


def test_utf8_plain(fixtures_dir: Path) -> None:
    path = fixtures_dir / "utf8.txt"
    path.write_text(RUSSIAN_TEXT, encoding="utf-8")
    decoded = read_text_file(path)
    assert decoded.encoding == "utf-8"
    assert decoded.text == RUSSIAN_TEXT


def test_utf8_bom(fixtures_dir: Path) -> None:
    path = fixtures_dir / "utf8_bom.txt"
    path.write_bytes(b"\xef\xbb\xbf" + RUSSIAN_TEXT.encode("utf-8"))
    decoded = read_text_file(path)
    assert decoded.encoding in ("utf-8-sig", "utf-8")
    assert decoded.text == RUSSIAN_TEXT
    assert not decoded.text.startswith("\ufeff")


def test_cp1251_russian(fixtures_dir: Path) -> None:
    path = fixtures_dir / "cp1251.txt"
    path.write_bytes(RUSSIAN_TEXT.encode("cp1251"))
    decoded = read_text_file(path)
    assert decoded.text == RUSSIAN_TEXT
    assert decoded.encoding in ("cp1251", "windows-1251", "CP1251")


def test_cp866_dos(fixtures_dir: Path) -> None:
    path = fixtures_dir / "cp866.txt"
    path.write_bytes(RUSSIAN_TEXT.encode("cp866"))
    decoded = read_text_file(path)
    assert decoded.text == RUSSIAN_TEXT


def test_latin1(fixtures_dir: Path) -> None:
    text = "Café résumé naïve"
    path = fixtures_dir / "latin1.txt"
    path.write_bytes(text.encode("latin-1"))
    decoded = read_text_file(path)
    assert decoded.text == text


def test_mixed_utf8_cp1251(fixtures_dir: Path) -> None:
    path = fixtures_dir / "valid_utf8.txt"
    text = "Hello мир 123"
    path.write_text(text, encoding="utf-8")
    decoded = read_text_file(path)
    assert decoded.encoding == "utf-8"
    assert decoded.text == text


def test_koi8r(fixtures_dir: Path) -> None:
    path = fixtures_dir / "koi8r.txt"
    path.write_bytes(RUSSIAN_TEXT.encode("koi8-r"))
    decoded = read_text_file(path)
    assert decoded.text == RUSSIAN_TEXT


def test_empty_file(fixtures_dir: Path) -> None:
    path = fixtures_dir / "empty.txt"
    path.write_bytes(b"")
    decoded = read_text_file(path)
    assert decoded.text == ""
    assert decoded.encoding == "utf-8"


def test_binary_garbage(fixtures_dir: Path) -> None:
    path = fixtures_dir / "garbage.bin"
    path.write_bytes(bytes(range(256)) * 4)
    decoded = read_text_file(path)
    assert isinstance(decoded.text, str)


def test_save_same_encoding(fixtures_dir: Path) -> None:
    src = fixtures_dir / "src_cp1251.txt"
    src.write_bytes(RUSSIAN_TEXT.encode("cp1251"))
    out = fixtures_dir / "out_cp1251.txt"
    write_text_file(out, RUSSIAN_TEXT, "cp1251")
    assert out.read_bytes() == RUSSIAN_TEXT.encode("cp1251")


def test_save_utf8_normalize(fixtures_dir: Path) -> None:
    out = fixtures_dir / "out_utf8.txt"
    write_text_file(out, RUSSIAN_TEXT, "utf-8")
    assert out.read_text(encoding="utf-8") == RUSSIAN_TEXT


def test_save_utf8_bom(fixtures_dir: Path) -> None:
    out = fixtures_dir / "out_bom.txt"
    write_text_file(out, "test", "utf-8-sig")
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")


def test_detect_encoding_utf8_bytes() -> None:
    raw = "тест".encode("utf-8")
    enc, conf = detect_encoding(raw)
    assert enc == "utf-8"
    assert conf > 0.5


def test_suggest_output_path() -> None:
    src = Path("readme.md")
    assert suggest_output_path(src, "_translated", "argos").name == "readme_translated.md"
    assert suggest_output_path(src, "_translated", "llm").name == "readme_translated_llm.md"


def test_resolve_output_encoding_same() -> None:
    assert resolve_output_encoding("cp1251", "same") == "cp1251"
    assert resolve_output_encoding("utf-8-sig", "same") == "utf-8"


def test_resolve_output_encoding_utf8() -> None:
    assert resolve_output_encoding("cp1251", "utf-8") == "utf-8"


def test_file_type_hint() -> None:
    from argos_translator.services.document_io import file_type_hint

    assert file_type_hint(Path("readme.md")) == "markdown"
    assert file_type_hint(Path("data.json")) == "json"
    assert file_type_hint(Path("notes.txt")) == "plain text"


def test_max_file_size(fixtures_dir: Path) -> None:
    path = fixtures_dir / "big.txt"
    path.write_bytes(b"x" * (2 * 1024 * 1024))
    from argos_translator.services.document_io import DocumentIOError

    with pytest.raises(DocumentIOError, match="большой"):
        read_text_file(path, max_size_mb=1)
