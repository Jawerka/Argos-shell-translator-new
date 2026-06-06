"""Автопроверки чеклиста «готово к релизу» (PLAN приложение B)."""

from __future__ import annotations

from pathlib import Path

from argos_translator.config.settings import AppSettings
from argos_translator.services.document_io import SUPPORTED_EXTENSIONS


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "argos_translator"


def test_default_theme_is_dark() -> None:
    assert AppSettings().theme == "dark"


def test_llm_enabled_by_default() -> None:
    assert AppSettings().llm.enabled is True


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


def test_plan_and_changelog_exist() -> None:
    assert (ROOT / "PLAN.md").is_file()
    assert (ROOT / "CHANGELOG.md").is_file()
