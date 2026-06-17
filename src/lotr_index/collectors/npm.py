from __future__ import annotations

import logging
from urllib.parse import quote

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)

NPM_REGISTRY = "https://registry.npmjs.org"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back, max_results
    results: list[Candidate] = []
    variants = ["", "-ml", "-ai", "-llm", "-js"]

    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            for suffix in variants:
                package = f"{alias.lower()}{suffix}"
                url = f"{NPM_REGISTRY}/{quote(package)}"
                try:
                    data = get_json(url, cache_namespace="npm")
                except Exception:
                    continue
                title = data.get("name") or package
                desc = data.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("npm", package, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="tool_name",
                    artifact_type="package",
                    domain="software package",
                    source_type="package_registry",
                    source_name="npm",
                    title=title,
                    url=f"https://www.npmjs.com/package/{package}",
                    package_name=package,
                    evidence_snippet=snippet,
                    raw_source_id=f"npm:{package}",
                ))
    return results
