from __future__ import annotations

from .model import Candidate
from .normalize import normalize_text


def dedupe_key(c: Candidate) -> str:
    if c.doi:
        return f"doi:{normalize_text(c.doi)}"
    if c.raw_source_id:
        return f"raw:{normalize_text(c.raw_source_id)}"
    if c.repo:
        return f"repo:{normalize_text(c.repo)}"
    if c.package_name and c.source_name:
        return f"pkg:{normalize_text(c.source_name)}:{normalize_text(c.package_name)}"
    return f"title:{normalize_text(c.title)}:{normalize_text(str(c.url))}"


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    best: dict[str, Candidate] = {}
    for c in candidates:
        key = dedupe_key(c)
        old = best.get(key)
        if old is None or c.confidence > old.confidence:
            best[key] = c
    return sorted(
        best.values(),
        key=lambda x: (-x.confidence, x.name.lower(), x.title.lower()),
    )
