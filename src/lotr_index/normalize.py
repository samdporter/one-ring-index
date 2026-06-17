from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

ACRONYM_EXPANSION_RE = re.compile(
    r"\b([A-Z][A-Z0-9]{2,16})\b\s*(?:[:=\-–—]|\(|,)\s*([A-Z][^\.\n]{8,240})",
    re.MULTILINE,
)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def stable_id(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def find_acronym_expansion(text: str | None, name: str) -> str | None:
    if not text:
        return None
    target = name.upper()
    for match in ACRONYM_EXPANSION_RE.finditer(text):
        acronym = match.group(1).upper()
        expansion = match.group(2).strip()
        if acronym == target:
            return expansion
    return None


def evidence_window(text: str | None, term: str, width: int = 180) -> str | None:
    if not text or not term:
        return None
    low = text.lower()
    idx = low.find(term.lower())
    if idx == -1:
        return None
    start = max(0, idx - width)
    end = min(len(text), idx + len(term) + width)
    snippet = text[start:end]
    return re.sub(r"\s+", " ", snippet).strip()
