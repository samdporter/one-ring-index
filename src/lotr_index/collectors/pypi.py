from __future__ import annotations

import logging

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back, max_results
    results: list[Candidate] = []
    variants = ["", "-ml", "-ai", "-torch", "-pytorch", "-llm"]

    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            for suffix in variants:
                package = f"{alias.lower()}{suffix}"
                url = f"https://pypi.org/pypi/{package}/json"
                try:
                    data = get_json(url, cache_namespace="pypi")
                except Exception:
                    continue
                info = data.get("info", {})
                title = info.get("name") or package
                summary = info.get("summary") or ""
                project_url = info.get("project_url") or f"https://pypi.org/project/{package}/"
                text = f"{title}. {summary}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("pypi", package, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="tool_name",
                    artifact_type="package",
                    domain="software package",
                    source_type="package_registry",
                    source_name="PyPI",
                    title=title,
                    url=project_url,
                    package_name=package,
                    evidence_snippet=snippet,
                    raw_source_id=f"pypi:{package}",
                ))
    return results
