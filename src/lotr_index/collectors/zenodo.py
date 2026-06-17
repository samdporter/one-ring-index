from __future__ import annotations

import logging

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

ZENODO_RECORDS = "https://zenodo.org/api/records"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "q": f"{alias} machine learning deep learning neural software benchmark dataset",
                "size": min(max_results, 20),
                "sort": "mostrecent",
            }
            try:
                data = get_json(ZENODO_RECORDS, params=params, cache_namespace="zenodo")
            except Exception as exc:
                log.warning("Zenodo query failed for %s: %s", alias, exc)
                continue
            for item in data.get("hits", {}).get("hits", []):
                metadata = item.get("metadata", {})
                title = metadata.get("title") or "unknown"
                desc = metadata.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                artifact_type = "software" if metadata.get("upload_type") == "software" else "unknown"
                results.append(Candidate(
                    id=stable_id("zenodo", item.get("id"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type=artifact_type,
                    domain="research artifact",
                    source_type="research_artifact",
                    source_name="Zenodo",
                    title=title,
                    authors=[c.get("name", "") for c in metadata.get("creators", [])],
                    published_date=metadata.get("publication_date"),
                    url=item.get("links", {}).get("html") or "https://zenodo.org/",
                    doi=metadata.get("doi"),
                    evidence_snippet=snippet,
                    raw_source_id=f"zenodo:{item.get('id')}",
                ))
    return results
