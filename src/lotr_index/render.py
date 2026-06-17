from __future__ import annotations

import csv
import json
from pathlib import Path

from .model import Candidate
from .storage import read_jsonl


def _load_candidates(path: str) -> list[Candidate]:
    return [Candidate(**row) for row in read_jsonl(path)]


def render_markdown(catalog: list[Candidate], candidates: list[Candidate]) -> None:
    docs = Path("docs")
    docs.mkdir(exist_ok=True)

    lines = [
        "# One Ring Index",
        "",
        "Daily-updated catalog of Tolkien / Lord-of-the-Rings-inspired names, acronyms, backronyms, benchmarks, datasets, models, packages, repositories, and software tools.",
        "",
        "## Confirmed and high-confidence entries",
        "",
        "| Name | Expansion | Type | Tolkien entity | Confidence | Source |",
        "|---|---|---|---|---:|---|",
    ]
    for c in catalog:
        expansion = c.expanded_form or "–"
        entity = c.tolkien_entity or "–"
        source = f"[{c.source_name}]({c.url})"
        lines.append(
            f"| {c.name} | {expansion} | {c.artifact_type} | {entity} | {c.confidence:.2f} | {source} |"
        )
    (docs / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    cand_lines = [
        "# Review Candidates",
        "",
        "These entries are plausible but need manual review.",
        "",
        "| Name | Title | Type | Confidence | Source | Evidence |",
        "|---|---|---|---:|---|---|",
    ]
    for c in candidates:
        source = f"[{c.source_name}]({c.url})"
        evidence = (c.evidence_snippet or "").replace("|", "\\|")
        cand_lines.append(
            f"| {c.name} | {c.title} | {c.artifact_type} | {c.confidence:.2f} | {source} | {evidence} |"
        )
    (docs / "candidates.md").write_text("\n".join(cand_lines) + "\n", encoding="utf-8")


def render_csv_json(catalog: list[Candidate]) -> None:
    docs = Path("docs")
    docs.mkdir(exist_ok=True)
    rows = [c.model_dump(mode="json") for c in catalog]
    (docs / "catalog.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    default_fields = [
        "id", "name", "expanded_form", "tolkien_entity", "match_kind", "artifact_type",
        "source_name", "title", "url", "confidence", "status",
    ]
    with (docs / "catalog.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else default_fields
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_all() -> None:
    catalog = _load_candidates("data/catalog.jsonl")
    review = _load_candidates("data/candidates.jsonl")
    render_markdown(catalog, review)
    render_csv_json(catalog)
