"""Утилиты для разбивки текста и определения языка."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

from argos_translator.config.constants import TranslationConstants
from argos_translator.utils.detect_log import detect_info, peek_words
from argos_translator.utils.imports import LINGUA_MODULE, LINGUA_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")

# Доля кириллицы для AUTO и для явной поправки. Подгоняется по корпусу lang_route.
_AUTO_RU_SHARE = 0.3
_EXPLICIT_RU_SHARE = 0.6
_EXPLICIT_MIN_LETTERS = 2
# Латиница: метка Lingua только на достаточно длинном уверенном тексте.
_MIN_LABEL_LATIN = 10
_MIN_LABEL_CONFIDENCE = 0.8
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_CYRILLIC_LANGS = frozenset({"ru", "bg", "uk", "mk", "sr", "be", "kk"})
_DEFAULT_FROM_CODES = frozenset({"en", "ru"})
# Низкая точность Lingua: без кириллических языков. Плюс установленные некириллические from.
_LABEL_LANGS = frozenset(
    {
        "en",
        "de",
        "fr",
        "es",
        "it",
        "pt",
        "nl",
        "pl",
        "cs",
        "tr",
        "sv",
        "ja",
        "zh",
        "ko",
        "ar",
        "el",
        "he",
        "hi",
        "th",
    }
)
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
_DISCORD_RE = re.compile(r"<@[!&]?\d+>|<#\d+>|<:[A-Za-z0-9_]+:\d+>")
_EMOJI_SHORT_RE = re.compile(r":[A-Za-z0-9_]{2,}:")
_SENTENCE_MARK_RE = re.compile(r"[.!?…\n\r]")

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


def _label_language_codes(installed: Optional[Iterable[str]] = None) -> frozenset[str]:
    """Набор меток: фиксированный low-accuracy список и установленные некириллические коды."""
    codes = set(_LABEL_LANGS)
    for code in TextUtils.installed_from_codes(installed):
        if code in _CYRILLIC_LANGS or code in {"auto", "ru"}:
            continue
        codes.add(code)
    return frozenset(codes)


def _get_lingua_detector(codes: frozenset[str]) -> Any | None:
    """Ленивый singleton LanguageDetector (low-accuracy) для набора меток."""
    if LINGUA_STATUS != ImportStatus.SUCCESS or LINGUA_MODULE is None:
        return None
    key = codes if codes else frozenset(_LABEL_LANGS)
    cached = _lingua_detectors.get(key)
    if cached is not None:
        return cached

    languages: list[Any] = []
    for code in sorted(key):
        lang = _lingua_language_for_code(code)
        if lang is not None:
            languages.append(lang)
    if not languages:
        return None

    builder_cls = getattr(LINGUA_MODULE, "LanguageDetectorBuilder", None)
    if builder_cls is None:
        return None
    try:
        built = builder_cls.from_languages(*languages)
        low = getattr(built, "with_low_accuracy_mode", None)
        if callable(low):
            built = low()
        detector = built.build()
    except Exception as exc:
        logger.debug("lingua detector build failed: %s", exc)
        return None
    _lingua_detectors[key] = detector
    return detector


def _is_letter(ch: str) -> bool:
    return unicodedata.category(ch).startswith("L")


def _is_digit(ch: str) -> bool:
    return unicodedata.category(ch).startswith("N")


def _script(ch: str) -> str:
    if not _is_letter(ch):
        return ""
    code = ord(ch)
    if (
        0x0400 <= code <= 0x052F
        or 0x1C80 <= code <= 0x1C8F
        or 0x2DE0 <= code <= 0x2DFF
        or 0xA640 <= code <= 0xA69F
    ):
        return "cyr"
    if (
        0x0041 <= code <= 0x005A
        or 0x0061 <= code <= 0x007A
        or 0x00C0 <= code <= 0x024F
        or 0x1E00 <= code <= 0x1EFF
    ):
        return "lat"
    return "other"


def _is_word_char(ch: str) -> bool:
    return _is_letter(ch) or _is_digit(ch) or ch in {"_", "'", "’"}


def _clean_lang_text(text: str) -> str:
    """Убрать URL, упоминания, короткие эмодзи и код — они не голосуют за язык."""
    cleaned = _FENCE_RE.sub(" ", text or "")
    cleaned = _INLINE_CODE_RE.sub(" ", cleaned)
    cleaned = _URL_RE.sub(" ", cleaned)
    cleaned = _EMAIL_RE.sub(" ", cleaned)
    cleaned = _DISCORD_RE.sub(" ", cleaned)
    cleaned = _EMOJI_SHORT_RE.sub(" ", cleaned)
    return cleaned


def _count_token(token: str, sentence_start: bool) -> Tuple[int, int, int]:
    cyr = 0
    other = 0
    latin: List[str] = []
    has_digit_or_underscore = False
    for ch in token:
        if _is_digit(ch) or ch == "_":
            has_digit_or_underscore = True
            continue
        if ch in {"'", "’"}:
            continue
        script = _script(ch)
        if script == "cyr":
            cyr += 1
        elif script == "lat":
            latin.append(ch)
        elif script == "other":
            other += 1
    lat = 0
    if latin and not has_digit_or_underscore:
        uppers = sum(1 for ch in latin if ch.isupper())
        internal_upper = any(ch.isupper() for ch in latin[1:])
        proper = latin[0].isupper() and not sentence_start
        all_caps = uppers == len(latin) and len(latin) >= 2
        if not (all_caps or internal_upper or proper):
            lat = len(latin)
    return cyr, lat, other


@dataclass(frozen=True)
class SourceVerdict:
    """Решение «русский или нет» и можно ли поправить явную пару en/ru."""

    auto: str
    explicit_fix: bool
    cyr: int
    lat: int
    other: int
    share: float

    @property
    def explicit_source(self) -> Optional[str]:
        if self.share >= _EXPLICIT_RU_SHARE and self.cyr >= _EXPLICIT_MIN_LETTERS:
            return "ru"
        if self.cyr == 0 and self.lat >= _EXPLICIT_MIN_LETTERS:
            return "en"
        return None


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
    def source_verdict(text: str) -> SourceVerdict:
        """Доля кириллицы после чистки. AUTO: ru при доле от 0.3, иначе other."""
        cleaned = _clean_lang_text(text or "")
        cyr = 0
        lat = 0
        other = 0
        sentence_start = True
        i = 0
        n = len(cleaned)
        while i < n:
            if not _is_word_char(cleaned[i]):
                if _SENTENCE_MARK_RE.match(cleaned[i]):
                    sentence_start = True
                i += 1
                continue
            start = i
            while i < n and _is_word_char(cleaned[i]):
                i += 1
            token_cyr, token_lat, token_other = _count_token(cleaned[start:i], sentence_start)
            cyr += token_cyr
            lat += token_lat
            other += token_other
            sentence_start = False
        total = cyr + lat + other
        share = (cyr / total) if total else 0.0
        auto = "ru" if total and share >= _AUTO_RU_SHARE else "other"
        verdict = SourceVerdict(
            auto=auto,
            explicit_fix=False,
            cyr=cyr,
            lat=lat,
            other=other,
            share=share,
        )
        return SourceVerdict(
            auto=verdict.auto,
            explicit_fix=verdict.explicit_source is not None,
            cyr=cyr,
            lat=lat,
            other=other,
            share=share,
        )

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
        text: str,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> str:
        """Свести метку к установленным from-кодам по вердикту, не по «любой кириллице»."""
        verdict = TextUtils.source_verdict(text)
        heuristic = "ru" if verdict.auto == "ru" else "en"
        code = (detected or "").strip().lower()
        if not code or code == "auto":
            return heuristic
        installed = TextUtils.installed_from_codes(installed_from_codes)
        if not installed:
            installed = set(_DEFAULT_FROM_CODES)
        if verdict.auto == "ru" and code not in _CYRILLIC_LANGS:
            return "ru" if "ru" in installed else heuristic
        if verdict.auto != "ru" and code in _CYRILLIC_LANGS:
            return "en" if "en" in installed else heuristic
        if code in installed:
            return code
        return heuristic

    @staticmethod
    def detect_parts(
        text: str,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> Tuple[str, str]:
        """Пара (код для Argos, метка без подгонки под модели)."""
        raw = text or ""
        stripped = raw.strip()
        peek = peek_words(stripped)
        verdict = TextUtils.source_verdict(raw)
        if not stripped:
            detect_info(
                "fn=detect_language branch=empty peek=%r len=0 cyr=0 lat=0 other=0 "
                "share=0.00 lang=en code=en",
                peek,
            )
            return "en", "en"

        lang = "en"
        confidence = 0.0
        branch = "verdict_ru" if verdict.auto == "ru" else "short_latin"
        top2 = ""
        latin_script = verdict.lat >= verdict.other and verdict.lat > 0
        if verdict.auto == "ru":
            lang = "ru"
            branch = "verdict_ru"
        elif latin_script and verdict.lat < _MIN_LABEL_LATIN:
            lang = "en"
            branch = "short_latin"
        else:
            lingua_codes = _label_language_codes(installed_from_codes)
            detector = _get_lingua_detector(lingua_codes)
            if detector is None:
                branch = "no_detector"
                lang = "en"
            else:
                try:
                    values = detector.compute_language_confidence_values(stripped)
                    if values:
                        parts: list[str] = []
                        for hit in values[:2]:
                            hit_lang = getattr(hit, "language", None)
                            conf = float(getattr(hit, "value", 0.0))
                            iso = (
                                getattr(hit_lang, "iso_code_639_1", None)
                                if hit_lang is not None
                                else None
                            )
                            code_name = getattr(iso, "name", None) if iso is not None else None
                            if code_name:
                                parts.append(f"{str(code_name).lower()}:{conf:.2f}")
                        top2 = ",".join(parts)
                        top = values[0]
                        hit_lang = getattr(top, "language", None)
                        confidence = float(getattr(top, "value", 0.0))
                        iso = (
                            getattr(hit_lang, "iso_code_639_1", None)
                            if hit_lang is not None
                            else None
                        )
                        code_name = getattr(iso, "name", None) if iso is not None else None
                        if code_name:
                            detected = str(code_name).lower()
                            if confidence >= _MIN_LABEL_CONFIDENCE:
                                lang = detected
                                branch = "lingua_ok"
                            else:
                                lang = "en"
                                branch = "low_confidence"
                            logger.debug("lingua -> %s (%.2f)", detected, confidence)
                        else:
                            branch = "lingua_empty"
                            lang = "en"
                    else:
                        branch = "lingua_empty"
                        lang = "en"
                except Exception as exc:
                    logger.debug("lingua failed: %s", exc)
                    branch = "lingua_fail"
                    lang = "en"
                    detect_info(
                        "fn=detect_language branch=lingua_fail peek=%r err=%s",
                        peek,
                        exc,
                    )

        code = TextUtils.snap_detected_lang(
            lang,
            text=raw,
            installed_from_codes=installed_from_codes,
        )
        detect_info(
            "fn=detect_language branch=%s peek=%r len=%s cyr=%s lat=%s other=%s "
            "share=%.2f lang=%s code=%s conf=%.2f top2=%s",
            branch,
            peek,
            len(stripped),
            verdict.cyr,
            verdict.lat,
            verdict.other,
            verdict.share,
            lang,
            code,
            confidence,
            top2 or "-",
        )
        return code, lang

    @staticmethod
    def detect_lang_tag(
        text: str,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> str:
        """ru или метка языка без подгонки под установленные модели."""
        return TextUtils.detect_parts(text, installed_from_codes=installed_from_codes)[1]

    @staticmethod
    def detect_language(
        text: str,
        installed_from_codes: Optional[Iterable[str]] = None,
    ) -> str:
        return TextUtils.detect_parts(text, installed_from_codes=installed_from_codes)[0]

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
