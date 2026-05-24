"""Lightweight i18n: JSON dictionaries + tr() lookup + change-signal manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

_DICT_DIR = Path(__file__).resolve().parent


class LanguageManager(QObject):
    language_changed = Signal(str)

    _instance: Optional["LanguageManager"] = None

    def __init__(self) -> None:
        super().__init__()
        self._lang: str = "en"
        self._dicts: Dict[str, Dict[str, str]] = {}
        self._load("en")

    @classmethod
    def instance(cls) -> "LanguageManager":
        if cls._instance is None:
            cls._instance = LanguageManager()
        return cls._instance

    def _load(self, lang: str) -> None:
        if lang in self._dicts:
            return
        path = _DICT_DIR / f"{lang}.json"
        if not path.exists():
            self._dicts[lang] = {}
            return
        with open(path, "r", encoding="utf-8") as f:
            self._dicts[lang] = json.load(f)

    def set_language(self, lang: str) -> None:
        if lang == self._lang:
            return
        self._load(lang)
        self._lang = lang
        self.language_changed.emit(lang)

    def current(self) -> str:
        return self._lang

    def available(self) -> list[str]:
        # Hardcoded so we list languages even if their JSON wasn't preloaded.
        return ["en", "zh"]

    def tr(self, key: str, **kwargs) -> str:
        text = self._dicts.get(self._lang, {}).get(key)
        if text is None:
            # Fall back to English then to the key itself.
            text = self._dicts.get("en", {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text


def tr(key: str, **kwargs) -> str:
    return LanguageManager.instance().tr(key, **kwargs)
