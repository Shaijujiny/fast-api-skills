"""i18n message keys. Every user-facing string is a key in app/locales/<lang>.json (all locales filled)."""

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
SUPPORTED_LANGUAGES = tuple(sorted(p.stem for p in LOCALES_DIR.glob("*.json")))


@lru_cache
def _catalog(lang: str) -> dict[str, str]:
    return json.loads((LOCALES_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def resolve_language(header: str | None) -> str:
    """Pick a supported language from an Accept-Language header, else the default."""
    for part in (header or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED_LANGUAGES:
            return code
    return get_settings().default_language


class Messages:
    """`messages.user_created` -> translated text. Missing keys fall back to English, then the key."""

    def __init__(self, lang: str) -> None:
        self._cat, self._fallback = _catalog(lang), _catalog("en")

    def has(self, key: str) -> bool:
        return key in self._cat or key in self._fallback

    def t(self, key: str) -> str:
        return self._cat.get(key) or self._fallback.get(key) or key

    def __getattr__(self, key: str) -> str:
        if key.startswith("_"):
            raise AttributeError(key)
        return self.t(key)


def get_messages(lang: str) -> Messages:
    return Messages(lang if lang in SUPPORTED_LANGUAGES else "en")
