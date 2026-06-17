from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    headers: dict[str, str] = {}
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if key:
        headers["x-api-key"] = key

    results: list[Candidate] = []
    for term_key, meta in terms.items():
        for alias in meta.get("aliases", [term_key])[:2]:
            params = {
                "query": f"{alias} machine learning deep learning neural software benchmark dataset",
                "limit": min(max_results, 20),
                "fields": "title,abstract,authors,year,url,externalIds,publicationDate",
            }
            try:
                data = get_json(
                    S2_SEARCH,
                    params=params,
                    headers=headers,
                    cache_namespace="semantic_scholar",
                    min_delay_seconds=1.1,
                )
            except Exception as exc:
                log.warning("Semantic Scholar query failed for %s: %s", alias, exc)
                continue
            for item in data.get("data", []):
                title = item.get("title") or "unknown"
                abstract = item.get("abstract") or ""
                text = f"{title}. {abstract}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                authors = [a.get("name", "") for a in item.get("authors", [])]
                doi = (item.get("externalIds") or {}).get("DOI")
                results.append(Candidate(
                    id=stable_id("semantic_scholar", item.get("paperId"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="Semantic Scholar",
                    title=title,
                    authors=authors,
                    year=item.get("year"),
                    published_date=item.get("publicationDate"),
                    url=item.get("url") or "https://www.semanticscholar.org/",
                    doi=doi,
                    evidence_snippet=snippet,
                    raw_source_id=f"s2:{item.get('paperId')}",
                ))
    return results
