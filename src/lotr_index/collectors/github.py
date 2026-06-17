from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)

GITHUB_SEARCH_REPOS = "https://api.github.com/search/repositories"


def _guess_artifact_type(text: str) -> str:
    low = text.lower()
    if "dataset" in low:
        return "dataset"
    if "benchmark" in low:
        return "benchmark"
    if "model" in low or "llm" in low:
        return "model"
    if "library" in low:
        return "library"
    return "repository"


def collect(terms: dict, days_back: int = 3, max_results: int = 50) -> list[Candidate]:
    del days_back
    token = os.getenv("GITHUB_TOKEN")
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    results: list[Candidate] = []
    for key, meta in terms.items():
        aliases = meta.get("aliases", [key])
        for alias in aliases[:2]:
            q = (
                f"{alias} machine-learning OR deep-learning OR LLM OR neural "
                "OR benchmark OR dataset in:name,description,readme"
            )
            params = {"q": q, "sort": "updated", "order": "desc", "per_page": max_results}
            try:
                data = get_json(
                    GITHUB_SEARCH_REPOS,
                    params=params,
                    headers=headers,
                    cache_namespace="github",
                )
            except Exception as exc:
                log.warning("GitHub query failed for %s: %s", alias, exc)
                continue

            for item in data.get("items", []):
                title = item.get("full_name") or item.get("name") or "unknown"
                desc = item.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("github", item.get("html_url"), alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="name_only",
                    artifact_type=_guess_artifact_type(text),
                    domain="software",
                    source_type="repository",
                    source_name="GitHub",
                    title=title,
                    authors=[item.get("owner", {}).get("login", "")],
                    published_date=item.get("created_at", "")[:10] or None,
                    updated_date=item.get("updated_at", "")[:10] or None,
                    url=item.get("html_url") or "https://github.com",
                    repo=item.get("full_name"),
                    evidence_snippet=snippet,
                    raw_source_id=f"github:{item.get('id')}",
                ))
    return results
