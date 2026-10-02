"""Корпус маршрута языка: вердикт AUTO и явная поправка, паритет с Dart."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from argos_translator.utils.imports import LINGUA_STATUS, ImportStatus
from argos_translator.utils.text_utils import TextUtils
from sidecar.jobs import ArgosJobRunner
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator

_CORPUS = Path(__file__).resolve().parent / "fixtures" / "lang_route" / "corpus.json"


def _rows() -> list[dict]:
    return json.loads(_CORPUS.read_text(encoding="utf-8"))


def test_corpus_auto_and_explicit_fix() -> None:
    failures: list[str] = []
    for row in _rows():
        verdict = TextUtils.source_verdict(row["text"])
        if verdict.auto != row["auto"] or verdict.explicit_fix != row["explicit_fix"]:
            failures.append(
                f"{row['id']} auto={verdict.auto}/{row['auto']} "
                f"fix={verdict.explicit_fix}/{row['explicit_fix']} "
                f"cyr={verdict.cyr} lat={verdict.lat} share={verdict.share:.2f}"
            )
    if failures:
        print("lang route corpus failed:", ", ".join(failures))
    assert failures == []


def test_log_replay_auto_pair_without_swaps() -> None:
    """На реальных префиксах AUTO сразу даёт итоговую пару."""
    failures: list[str] = []
    for row in _rows():
        if row["origin"] != "log":
            continue
        verdict = TextUtils.source_verdict(row["text"])
        pair = ("ru", "en") if verdict.auto == "ru" else ("en", "ru")
        expected = ("ru", "en") if row["auto"] == "ru" else ("en", "ru")
        if pair != expected:
            failures.append(row["id"])
    if failures:
        print("lang route replay failed:", ", ".join(failures))
    assert failures == []


def test_anchor_counts_match_dart() -> None:
    cases = {
        "Эти два?": (6, 0, 0, "ru", True),
        "knee_together": (0, 0, 0, "other", False),
        "The word гардиент means gradient in my notes": (8, 29, 0, "other", False),
        "Запусти docker compose up и посмотри logs в Grafana": (17, 19, 0, "ru", False),
        "OK": (0, 0, 0, "other", False),
        "Да": (2, 0, 0, "ru", True),
    }
    for text, (cyr, lat, other, auto, fix) in cases.items():
        verdict = TextUtils.source_verdict(text)
        assert (verdict.cyr, verdict.lat, verdict.other, verdict.auto, verdict.explicit_fix) == (
            cyr,
            lat,
            other,
            auto,
            fix,
        )


def test_label_languages_with_lingua() -> None:
    if LINGUA_STATUS != ImportStatus.SUCCESS:
        pytest.skip("lingua is not installed")
    samples = {
        "de": "Russland ist nicht unsere friend, aber das Wetter heute ist wirklich kalt und grau",
        "fr": "Bonjour, comment allez-vous aujourd'hui dans cette belle ville",
        "es": "Hola, buenos dias, como estas esta manana en la ciudad",
        "pl": "Czesc, jak sie masz dzisiaj w tym pieknym miescie nad rzeka",
        "ja": "今日はとてもいい天気ですね。散歩に行きましょう。",
        "zh": "今天天气很好，我们一起去公园散步吧。",
        "ko": "오늘 날씨가 정말 좋습니다. 같이 산책하러 갈까요.",
    }
    for code, text in samples.items():
        assert TextUtils.detect_lang_tag(text) == code
    assert TextUtils.detect_lang_tag("lol") == "en"
    assert TextUtils.detect_lang_tag("OK") == "en"


def test_corpus_labels_with_lingua() -> None:
    if LINGUA_STATUS != ImportStatus.SUCCESS:
        pytest.skip("lingua is not installed")
    failures: list[str] = []
    for row in _rows():
        label = row.get("label")
        if not label:
            continue
        got = TextUtils.detect_lang_tag(row["text"])
        if got != label:
            failures.append(f"{row['id']} {got}!={label}")
    if failures:
        print("lang labels failed:", ", ".join(failures))
    assert failures == []


def test_snap_missing_german_word_from_corpus_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    pairs = ["en->ru", "ru->en"]
    monkeypatch.setattr(runner.model_manager, "list_installed_pairs", lambda: list(pairs))
    monkeypatch.setattr(
        runner.model_manager,
        "has_pair",
        lambda from_code, to_code: f"{from_code}->{to_code}" in pairs,
    )
    text = "Das Wetter heute ist wirklich sehr kalt und grau, слово"
    assert runner._snap_missing_pair(text, "de", "ru", "ru") == ("en", "ru")
