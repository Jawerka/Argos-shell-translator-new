"""Автопроверки чеклиста «готово к релизу»."""

from __future__ import annotations

from pathlib import Path

from argos_translator.services.document_io import SUPPORTED_EXTENSIONS


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "argos_translator"


def test_supported_document_extensions() -> None:
    assert ".txt" in SUPPORTED_EXTENSIONS
    assert ".md" in SUPPORTED_EXTENSIONS


def test_readme_covers_key_topics() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for topic in ("LLM", "settings.json", "log/app_debug.log", "pytest"):
        assert topic.lower() in readme.lower()


def test_no_debug_print_in_src() -> None:
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert 'print("DEBUG' not in text
        assert "print('DEBUG" not in text


def test_changelog_exists() -> None:
    assert (ROOT / "CHANGELOG.md").is_file()
