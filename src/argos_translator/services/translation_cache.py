"""LRU-кэш переводов Argos в рамках сессии."""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional, Tuple


class TranslationCache:
    def __init__(self, max_size: int = 500) -> None:
        self.max_size = max(1, max_size)
        self._store: OrderedDict[Tuple[str, str, str], str] = OrderedDict()

    def _key(self, text: str, from_code: str, to_code: str) -> Tuple[str, str, str]:
        return (from_code, to_code, text)

    def get(self, text: str, from_code: str, to_code: str) -> Optional[str]:
        key = self._key(text, from_code, to_code)
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, text: str, from_code: str, to_code: str, translation: str) -> None:
        key = self._key(text, from_code, to_code)
        self._store[key] = translation
        self._store.move_to_end(key)
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()
