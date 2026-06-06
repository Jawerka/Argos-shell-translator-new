"""Чтение и запись текстовых файлов с автоопределением кодировки (D8)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Tuple

logger = logging.getLogger("ArgosStreaming")

SUPPORTED_EXTENSIONS: Set[str] = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".log",
    ".rst",
    ".toml",
}

SAMPLE_SIZE = 64 * 1024
FALLBACK_ENCODINGS = ("utf-8", "cp1251", "cp866", "koi8-r", "iso-8859-5", "latin-1", "iso-8859-1")

BOM_SIGNATURES = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


class DocumentIOError(Exception):
    pass


@dataclass
class DecodedFile:
    text: str
    encoding: str
    confidence: float
    path: Path


def is_supported_extension(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def file_type_hint(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".md", ".markdown", ".rst"):
        return "markdown"
    if ext in (".html", ".htm", ".xml"):
        return "html"
    if ext == ".json":
        return "json"
    if ext in (".yaml", ".yml"):
        return "yaml"
    if ext == ".csv":
        return "csv"
    return "plain text"


def _readable_ratio(text: str) -> float:
    if not text:
        return 1.0
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t")
    return printable / len(text)


def _cyrillic_ratio(text: str) -> float:
    if not text:
        return 0.0
    cyr = sum(1 for ch in text if "\u0400" <= ch <= "\u04FF" or ch in "ёЁ")
    return cyr / len(text)


def _russian_word_hits(text: str) -> int:
    lower = text.lower()
    words = ("привет", "мир", "тест", "это", "что", "как", "для", "или", "кодировк")
    return sum(1 for word in words if word in lower)


def _latin_accent_hits(text: str) -> int:
    return sum(1 for ch in text if ch in "àáâãäåèéêëìíîïñòóôõöùúûüýÿç")


def _looks_like_cyrillic_bytes(sample: bytes) -> bool:
    if not sample:
        return False
    high = [b for b in sample if b >= 0x80]
    if len(high) < 3:
        return False
    high_ratio = len(high) / len(sample)
    dense = sum(1 for b in high if b >= 0xC0)
    return high_ratio > 0.30 and dense / len(high) > 0.5


def _encoding_quality(text: str) -> float:
    return _cyrillic_ratio(text) * 2.0 + _russian_word_hits(text) * 0.4


def _best_cyrillic_encoding(raw: bytes) -> Optional[Tuple[str, str, float]]:
    best: Optional[Tuple[str, str, float]] = None
    for enc in ("utf-8", "cp1251", "cp866", "koi8-r", "iso-8859-5"):
        text = _try_decode(raw, enc)
        if text is None or _readable_ratio(text) < 0.9:
            continue
        quality = _encoding_quality(text)
        if _russian_word_hits(text) == 0 and _cyrillic_ratio(text) < 0.35:
            continue
        if best is None or quality > best[2]:
            best = (text, enc, quality)
    if best is None or best[2] < 0.35:
        return None
    return best


def _try_decode(raw: bytes, encoding: str) -> Optional[str]:
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return None


def detect_encoding(raw: bytes) -> Tuple[str, float]:
    if not raw:
        return "utf-8", 1.0

    sample = raw[:SAMPLE_SIZE]

    for bom, enc in BOM_SIGNATURES:
        if sample.startswith(bom):
            text = _try_decode(raw, enc)
            if text is not None:
                if enc == "utf-8-sig" and text.startswith("\ufeff"):
                    text = text[1:]
                return enc, 1.0

    utf8_text = _try_decode(sample, "utf-8")
    if utf8_text is not None and _readable_ratio(utf8_text) > 0.95:
        full = _try_decode(raw, "utf-8")
        if full is not None:
            return "utf-8", 0.99

    if (
        re.search(rb"[\x80-\xff]", sample)
        and not re.search(rb"[\xc0-\xff][\x80-\xbf]{1,2}", sample)
        and not _looks_like_cyrillic_bytes(sample)
    ):
        latin_text = _try_decode(raw, "latin-1")
        if latin_text is not None and _readable_ratio(latin_text) > 0.95:
            if _latin_accent_hits(latin_text) >= 1 and _russian_word_hits(latin_text) == 0:
                return "latin-1", 0.88
            if _cyrillic_ratio(latin_text) < 0.05:
                return "latin-1", 0.85

    cyr_best = _best_cyrillic_encoding(raw)
    if cyr_best is not None:
        _text, enc, quality = cyr_best
        return enc, min(0.95, 0.65 + quality * 0.2)

    try:
        from charset_normalizer import from_bytes

        result = from_bytes(sample).best()
        if result is not None:
            enc = (result.encoding or "utf-8").lower()
            coherence = getattr(result, "coherence", None)
            confidence = float(coherence) if coherence is not None else 0.8
            text = _try_decode(raw, enc)
            if text is not None and _readable_ratio(text) > 0.85:
                latin_text = _try_decode(raw, "latin-1")
                if (
                    latin_text
                    and _latin_accent_hits(latin_text) >= 2
                    and _russian_word_hits(latin_text) == 0
                    and _latin_accent_hits(latin_text) > _latin_accent_hits(text)
                ):
                    return "latin-1", 0.88
                if cyr_best := _best_cyrillic_encoding(raw):
                    if _encoding_quality(text) < cyr_best[2] * 0.6:
                        return cyr_best[1], min(0.95, 0.65 + cyr_best[2] * 0.2)
                return enc, min(max(confidence, 0.5), 0.98)
    except Exception as exc:
        logger.debug("charset-normalizer failed: %s", exc)

    for enc in FALLBACK_ENCODINGS:
        text = _try_decode(raw, enc)
        if text is not None and _readable_ratio(text) > 0.95:
            return enc, 0.6

    logger.warning("Encoding detection fallback to utf-8 with replace")
    return "utf-8", 0.1


def read_text_file(path: Path, max_size_mb: int = 10) -> DecodedFile:
    path = Path(path)
    if not path.is_file():
        raise DocumentIOError(f"Файл не найден: {path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise DocumentIOError(f"Файл слишком большой ({size_mb:.1f} MB, лимит {max_size_mb} MB)")

    raw = path.read_bytes()
    if not raw:
        logger.debug("detected encoding=utf-8 confidence=1.0 path=%s (empty)", path.name)
        return DecodedFile(text="", encoding="utf-8", confidence=1.0, path=path)

    encoding, confidence = detect_encoding(raw)
    text = _try_decode(raw, encoding)
    if text is None:
        text = raw.decode("utf-8", errors="replace")
        encoding = "utf-8"
        logger.warning("decode failed, using utf-8 replace for %s", path.name)

    if encoding == "utf-8-sig" and text.startswith("\ufeff"):
        text = text[1:]

    logger.debug(
        "detected encoding=%s confidence=%.2f path=%s",
        encoding,
        confidence,
        path.name,
    )
    return DecodedFile(text=text, encoding=encoding, confidence=confidence, path=path)


def resolve_output_encoding(source_encoding: str, output_mode: str) -> str:
    mode = (output_mode or "same").lower()
    if mode == "same":
        return source_encoding if source_encoding != "utf-8-sig" else "utf-8"
    return mode


def write_text_file(path: Path, content: str, encoding: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    enc = encoding
    if enc == "utf-8-sig":
        path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
        return
    path.write_text(content, encoding=enc, errors="strict")


def suggest_output_path(src: Path, suffix: str = "_translated", engine: str = "argos") -> Path:
    src = Path(src)
    stem = src.stem
    ext = src.suffix
    clean_suffix = suffix or "_translated"
    if engine == "llm":
        return src.with_name(f"{stem}{clean_suffix}_llm{ext}")
    return src.with_name(f"{stem}{clean_suffix}{ext}")
