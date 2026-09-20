"""Утилиты для разбивки текста и определения языка."""

from __future__ import annotations

import logging
import re
from typing import Any, Iterable, List, Optional, Tuple

from argos_translator.config.constants import TranslationConstants
from argos_translator.utils.detect_log import detect_info, peek_words
from argos_translator.utils.imports import LINGUA_MODULE, LINGUA_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")

# 1–2 символа слишком мало даже для Lingua; ниже порога confidence — эвристика.
_MIN_LINGUA_CHARS = 3
_MIN_LINGUA_CONFIDENCE = 0.5
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_CYRILLIC_LANGS = frozenset({"ru", "bg", "uk", "mk", "sr", "be", "kk"})
_DEFAULT_FROM_CODES = frozenset({"en", "ru"})

# Кэш детекторов: frozenset(iso) → detector
_lingua_detectors: dict[frozenset[str], Any] = {}


def _lingua_language_for_code(code: str) -> Any | None:
    """ISO-639-1 → Language enum Lingua, либо None если код неизвестен."""
    if LINGUA_MODULE is None:
        return None
    iso_cls = getattr(LINGUA_MODULE, "IsoCode639_1", None)
    language_cls = getattr(LINGUA_MODULE, "Language", None)
    if iso_cls is None or language_cls is None:
        return None
    iso = getattr(iso_cls, code.upper(), None)
    if iso is None:
        return None
    try:
        return language_cls.from_iso_code_639_1(iso)
    except Exception:
        return None


def _get_lingua_detector(codes: frozenset[str]) -> Any | None:
    """Ленивый singleton LanguageDetector для набора установленных from-кодов."""
    if LINGUA_STATUS != ImportStatus.SUCCESS or LINGUA_MODULE is None:
        return None
    key = codes if codes else frozenset(_DEFAULT_FROM_CODES)
    cached = _lingua_detectors.get(key)
    if cached is not None:
        return cached

    languages: list[Any] = []
    for code in sorted(key):
        lang = _lingua_language_for_code(code)
        if lang is not None:
            languages.append(lang)
    if not languages:
        for code in sorted(_DEFAULT_FROM_CODES):
            lang = _lingua_language_for_code(code)
            if lang is not None:
                languages.append(lang)
    if not languages:
        return None

    builder_cls = getattr(LINGUA_MODULE, "LanguageDetectorBuilder", None)
    if builder_cls is None:
        return None
    try:
        detector = builder_cls.from_languages(*languages).build()
    except Exception as exc:
        logger.debug("lingua detector build failed: %s", exc)
        return None
    _lingua_detectors[key] = detector
    return detector


class TextUtils:
    SENTENCE_REGEX = re.compile(r"(?<=\S[.!?…])\s+(?=[A-ZА-ЯЁ0-9\"'«\"])")
    CODE_FENCE_REGEX = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)

    @staticmethod
    def split_prose_and_code_fences(text: str) -> List[Tuple[str, bool]]:
        """Разбить текст на сегменты: (фрагмент, translatable). False = fenced code block."""
        if not text:
            return []
        segments: List[Tuple[str, bool]] = []
        pos = 0
        for match in TextUtils.CODE_FENCE_REGEX.finditer(text):
            if match.start() > pos:
                segments.append((text[pos : match.start()], True))
            segments.append((match.group(0), False))
            pos = match.end()
        if pos < len(text):
            segments.append((text[pos:], True))
        if not segments:
            segments.append((text, True))
        return segments

    @staticmethod
    def has_cyrillic(text: str) -> bool:
        return bool(_CYRILLIC_RE.search(text or ""))

    @staticmethod
    def installed_from_codes(pairs: Optional[Iterable[str]] = None) -> set[str]:
        """Исходные коды из пар `en->ru` / `en-ru` или уже готовые `en`."""
        out: set[str] = set()
        for raw in pairs or []:
            item = str(raw).strip().lower().replace("→", "->")
            if not item:
                continue
            if "->" in item:
                item = item.split("->", 1)[0].strip()
            elif "-" in item:
                item = item.split("-", 1)[0].strip()
            if item:
                out.add(item)
        return out

    @staticmethod
    def snap_detected_lang(
        detected: str,
        *,
        has_cyrillic: bool,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> str:
        """Свести детект к установленным from-кодам, иначе en/ru по алфавиту."""
        heuristic = "ru" if has_cyrillic else "en"
        code = (detected or "").strip().lower()
        if not code or code == "auto":
            return heuristic
        installed = TextUtils.installed_from_codes(installed_from_codes)
        if not installed:
            installed = set(_DEFAULT_FROM_CODES)
        if has_cyrillic and code not in _CYRILLIC_LANGS:
            return "ru" if "ru" in installed else heuristic
        if not has_cyrillic and code in _CYRILLIC_LANGS:
            return "en" if "en" in installed else heuristic
        if code in installed:
            return code
        return heuristic

    @staticmethod
    def detect_language(
        text: str,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> str:
        text = (text or "").strip()
        peek = peek_words(text)
        if not text:
            detect_info("fn=detect_language branch=empty peek=%r final=en", peek)
            return "en"

        cyrillic = TextUtils.has_cyrillic(text)
        heuristic = "ru" if cyrillic else "en"

        def _snap(code: str) -> str:
            return TextUtils.snap_detected_lang(
                code,
                has_cyrillic=cyrillic,
                installed_from_codes=installed_from_codes,
            )

        if len(text) < _MIN_LINGUA_CHARS:
            final = _snap(heuristic)
            detect_info(
                "fn=detect_language branch=tiny_text peek=%r len=%s cyrillic=%s "
                "heuristic=%s final=%s",
                peek,
                len(text),
                cyrillic,
                heuristic,
                final,
            )
            return final

        installed = TextUtils.installed_from_codes(installed_from_codes)
        if not installed:
            installed = set(_DEFAULT_FROM_CODES)

        lingua_status = (
            LINGUA_STATUS.value if isinstance(LINGUA_STATUS, ImportStatus) else str(LINGUA_STATUS)
        )
        detected = heuristic
        confidence = 0.0
        branch = "no_detector"
        top2 = ""
        detector = _get_lingua_detector(frozenset(installed))
        if detector is None:
            branch = "no_detector"
        else:
            try:
                values = detector.compute_language_confidence_values(text)
                if values:
                    parts: list[str] = []
                    for hit in values[:2]:
                        lang = getattr(hit, "language", None)
                        conf = float(getattr(hit, "value", 0.0))
                        iso = getattr(lang, "iso_code_639_1", None) if lang is not None else None
                        code_name = getattr(iso, "name", None) if iso is not None else None
                        if code_name:
                            parts.append(f"{str(code_name).lower()}:{conf:.2f}")
                    top2 = ",".join(parts)
                    top = values[0]
                    lang = getattr(top, "language", None)
                    confidence = float(getattr(top, "value", 0.0))
                    iso = getattr(lang, "iso_code_639_1", None) if lang is not None else None
                    code_name = getattr(iso, "name", None) if iso is not None else None
                    if code_name:
                        detected = str(code_name).lower()
                        branch = "lingua_ok"
                        logger.debug("lingua -> %s (%.2f)", detected, confidence)
                    else:
                        branch = "lingua_empty"
                else:
                    branch = "lingua_empty"
            except Exception as exc:
                logger.debug("lingua failed: %s", exc)
                detected = heuristic
                confidence = 0.0
                branch = "lingua_fail"
                detect_info(
                    "fn=detect_language branch=lingua_fail peek=%r err=%s",
                    peek,
                    exc,
                )

        raw_code = detected
        after_threshold = detected
        if confidence < _MIN_LINGUA_CONFIDENCE and branch in {
            "lingua_ok",
            "lingua_empty",
            "no_detector",
        }:
            if branch == "lingua_ok" and confidence < _MIN_LINGUA_CONFIDENCE:
                branch = "low_confidence"
            after_threshold = heuristic
            detected = heuristic

        final = _snap(detected)
        detect_info(
            "fn=detect_language branch=%s peek=%r len=%s installed=%s lingua_status=%s "
            "cyrillic=%s heuristic=%s raw=%s conf=%.2f top2=%s after_threshold=%s "
            "snap_in=%s final=%s",
            branch,
            peek,
            len(text),
            sorted(installed),
            lingua_status,
            cyrillic,
            heuristic,
            raw_code,
            confidence,
            top2 or "-",
            after_threshold,
            detected,
            final,
        )
        return final

    @staticmethod
    def resolve_auto_pair(detected: str, preferred_to: str) -> Tuple[str, str]:
        """AUTO: предпочтительная цель; при совпадении с детектом — переворот ru↔en."""
        from_code = (detected or "").strip().lower() or "en"
        preferred = (preferred_to or "").strip().lower() or "ru"
        if from_code == preferred:
            to_code = "en" if from_code == "ru" else "ru"
        else:
            to_code = preferred
        return from_code, to_code

    @staticmethod
    def split_into_paragraphs(text: str) -> List[str]:
        if not text or not text.strip():
            return []
        parts = re.split(r"\n{2,}", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def split_paragraph_into_sentences(paragraph: str) -> List[str]:
        paragraph = (paragraph or "").strip()
        if not paragraph:
            return []
        try:
            sentences = TextUtils.SENTENCE_REGEX.split(paragraph)
        except Exception:
            sentences = [paragraph]

        if len(sentences) == 1 and len(paragraph) > TranslationConstants.MAX_CHARS_PER_CHUNK:
            return TextUtils._fallback_split_by_words(paragraph)

        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _fallback_split_by_words(text: str) -> List[str]:
        words = text.split()
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for word in words:
            current.append(word)
            current_len += len(word) + 1
            if current_len >= TranslationConstants.MAX_CHARS_PER_CHUNK:
                chunks.append(" ".join(current))
                current = []
                current_len = 0

        if current:
            chunks.append(" ".join(current))
        return chunks

    @staticmethod
    def make_sentence_chunks(
        sentences: List[str],
        max_chars: int = TranslationConstants.MAX_CHARS_PER_CHUNK,
        overlap: int = TranslationConstants.SENTENCE_WINDOW,
    ) -> List[Tuple[int, int]]:
        if not sentences:
            return []

        ranges: List[Tuple[int, int]] = []
        n = len(sentences)
        i = 0

        while i < n:
            cur_len = 0
            j = i
            while j < n and (cur_len + len(sentences[j]) + 1) <= max_chars:
                cur_len += len(sentences[j]) + 1
                j += 1
            if j == i:
                j = i + 1
            ranges.append((i, j))
            if j >= n:
                break
            i = max(j - overlap, j)
        return ranges

    @staticmethod
    def build_argos_units(
        text: str,
        *,
        translate_code_blocks: bool = True,
    ) -> List[Tuple[str, int, bool]]:
        """Собрать чанки для Argos: (текст_чанка, индекс_параграфа, переводить?)."""
        units: List[Tuple[str, int, bool]] = []
        paragraph_index = 0

        for segment, segment_translatable in TextUtils.split_prose_and_code_fences(text):
            if not segment.strip():
                continue

            if not translate_code_blocks and not segment_translatable:
                units.append((segment, paragraph_index, False))
                paragraph_index += 1
                continue

            for paragraph in TextUtils.split_into_paragraphs(segment):
                sentences = TextUtils.split_paragraph_into_sentences(paragraph)
                if not sentences:
                    continue
                for start, end in TextUtils.make_sentence_chunks(sentences):
                    chunk_text = " ".join(sentences[start:end])
                    if chunk_text.strip():
                        units.append((chunk_text, paragraph_index, True))
                paragraph_index += 1

        return units
