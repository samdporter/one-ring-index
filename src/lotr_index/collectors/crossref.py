from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

CROSSREF_WORKS = "https://api.crossref.org/works"


def collect(terms: dict, days_back: int = 3, max_results: int = 50) -> list[Candidate]:
    del days_back
    contact = os.getenv("CONTACT_EMAIL", "unknown@example.com")
    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "query.bibliographic": (
                    f"{alias} machine learning deep learning neural software benchmark dataset"
                ),
                "rows": min(max_results, 20),
                "mailto": contact,
            }
            try:
                data = get_json(CROSSREF_WORKS, params=params, cache_namespace="crossref")
            except Exception as exc:
                log.warning("Crossref query failed for %s: %s", alias, exc)
                continue
            for item in data.get("message", {}).get("items", []):
                title = " ".join(item.get("title", [])[:1]) or "unknown"
                text = title
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                doi = item.get("DOI")
                results.append(Candidate(
                    id=stable_id("crossref", doi or item.get("URL"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="Crossref",
                    title=title,
                    url=item.get("URL") or (f"https://doi.org/{doi}" if doi else "https://www.crossref.org"),
                    doi=doi,
                    evidence_snippet=snippet,
                    raw_source_id=f"crossref:{doi}",
                ))
    return results
