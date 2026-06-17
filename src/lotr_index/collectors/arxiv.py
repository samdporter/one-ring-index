from __future__ import annotations

import logging
import os
import time
from urllib.parse import urlencode

import feedparser
import httpx

from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"


def _guess_artifact_type(text: str) -> str:
    low = text.lower()
    if "benchmark" in low:
        return "benchmark"
    if "dataset" in low:
        return "dataset"
    if "model" in low:
        return "model"
    if "software" in low or "tool" in low or "framework" in low:
        return "tool"
    return "paper"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    results: list[Candidate] = []
    contact = os.getenv("CONTACT_EMAIL", "unknown@example.com")
    headers = {"User-Agent": f"one-ring-index/0.1 (mailto:{contact})"}

    for key, meta in terms.items():
        aliases = meta.get("aliases", [key])
        for alias in aliases[:2]:
            query = (
                f'all:"{alias}" AND ('
                'all:"machine learning" OR all:"deep learning" OR all:"neural" '
                'OR all:"LLM" OR all:"benchmark" OR all:"dataset" OR all:"software")'
            )
            params = {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending",
            }
            url = f"{ARXIV_API}?{urlencode(params)}"
            try:
                time.sleep(3.1)
                response = httpx.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
            except Exception as exc:
                log.warning("arXiv query failed for %s: %s", alias, exc)
                continue

            for entry in feed.entries:
                title = entry.get("title", "").replace("\n", " ").strip()
                summary = entry.get("summary", "").replace("\n", " ").strip()
                text = f"{title}. {summary}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                match_kind = "full_acronym" if expansion else "name_only"
                arxiv_id = entry.get("id", "")
                authors = [a.get("name", "") for a in entry.get("authors", [])]
                published = entry.get("published", "")[:10] or None
                year = int(published[:4]) if published and published[:4].isdigit() else None

                results.append(Candidate(
                    id=stable_id("arxiv", arxiv_id, alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind=match_kind,
                    artifact_type=_guess_artifact_type(text),
                    domain="machine learning / software",
                    source_type="paper",
                    source_name="arXiv",
                    title=title,
                    authors=authors,
                    year=year,
                    published_date=published,
                    updated_date=entry.get("updated", "")[:10] or None,
                    url=arxiv_id or entry.get("link", "https://arxiv.org"),
                    evidence_snippet=snippet,
                    raw_source_id=f"arxiv:{arxiv_id}",
                ))
    return results
