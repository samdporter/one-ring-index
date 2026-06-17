from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

OPENALEX_WORKS = "https://api.openalex.org/works"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    api_key = os.getenv("OPENALEX_API_KEY")
    if not api_key:
        log.info("OPENALEX_API_KEY not set; skipping OpenAlex")
        return []

    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "search": f"{alias} machine learning deep learning neural software benchmark dataset",
                "per-page": min(max_results, 25),
                "api_key": api_key,
            }
            try:
                data = get_json(OPENALEX_WORKS, params=params, cache_namespace="openalex")
            except Exception as exc:
                log.warning("OpenAlex query failed for %s: %s", alias, exc)
                continue
            for item in data.get("results", []):
                title = item.get("title") or "unknown"
                text = title
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                results.append(Candidate(
                    id=stable_id("openalex", item.get("id"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="OpenAlex",
                    title=title,
                    year=item.get("publication_year"),
                    published_date=item.get("publication_date"),
                    url=item.get("doi") or item.get("id") or "https://openalex.org",
                    doi=item.get("doi"),
                    evidence_snippet=snippet,
                    raw_source_id=f"openalex:{item.get('id')}",
                ))
    return results
