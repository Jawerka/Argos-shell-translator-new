"""Утилиты для разбивки текста и определения языка."""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from argos_translator.config.constants import TranslationConstants
from argos_translator.utils.imports import LANGDETECT_MODULE, LANGDETECT_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")

# Короткие фразы langdetect часто путает (en↔nl, ru↔bg); ниже порога — только по алфавиту.
_MIN_LANGDETECT_CHARS = 20


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
    def detect_language(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "en"

        if re.search(r"[А-Яа-яЁё]", text):
            cyrillic_default = "ru"
        else:
            cyrillic_default = None

        if len(text) < _MIN_LANGDETECT_CHARS:
            return cyrillic_default or "en"

        if LANGDETECT_STATUS == ImportStatus.SUCCESS and LANGDETECT_MODULE is not None:
            try:
                detect_fn = getattr(LANGDETECT_MODULE, "detect_langs", None)
                if callable(detect_fn):
                    results = detect_fn(text)
                    if results:
                        top = results[0]
                        code = getattr(top, "lang", None)
                        prob = float(getattr(top, "prob", 0.0))
                        if code:
                            code = code.lower()
                            logger.debug("langdetect -> %s (%.2f)", code, prob)
                            if cyrillic_default:
                                if code == "ru":
                                    return "ru"
                                if len(text) < 120 and code in ("bg", "uk", "mk", "sr"):
                                    return "ru"
                                return code
                            return code
            except Exception as exc:
                logger.debug("langdetect failed: %s", exc)

        return cyrillic_default or "en"

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
