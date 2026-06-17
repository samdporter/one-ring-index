from __future__ import annotations

import argparse
import importlib
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from .dedupe import dedupe
from .logging_config import configure_logging
from .model import Candidate
from .render import render_all
from .score import score_candidate
from .storage import ensure_dirs, read_jsonl, write_jsonl

console = Console()

COLLECTORS = [
    "arxiv",
    "github",
    "huggingface",
    "openalex",
    "crossref",
    "semantic_scholar",
    "pypi",
    "npm",
    "zenodo",
]


def load_yaml(path: str) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def flatten_terms(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for group in ["high_precision", "medium_precision", "low_precision"]:
        for key, value in config.get(group, {}).items():
            item = dict(value)
            item["precision_group"] = group
            out[key] = item
    return out


def term_weight_by_entity(terms: dict[str, dict[str, Any]], entity: str | None) -> float:
    if not entity:
        return 0.50
    for meta in terms.values():
        if meta.get("entity") == entity:
            return float(meta.get("weight", 0.50))
    return 0.50


def run_sweep(days_back: int, source: str | None) -> None:
    ensure_dirs()
    term_config = load_yaml("config/tolkien_terms.yml")
    terms = flatten_terms(term_config)

    selected = [source] if source else COLLECTORS
    all_candidates: list[Candidate] = []

    for collector_name in selected:
        if collector_name not in COLLECTORS:
            raise SystemExit(f"Unknown source: {collector_name}")
        console.print(f"[bold]Collecting from {collector_name}[/bold]")
        module = importlib.import_module(f"lotr_index.collectors.{collector_name}")
        try:
            found = module.collect(terms, days_back=days_back)
        except Exception as exc:
            console.print(f"[red]Collector failed: {collector_name}: {exc}[/red]")
            found = []
        console.print(f"  found {len(found)} raw candidates")
        all_candidates.extend(found)

    scored: list[Candidate] = []
    for c in all_candidates:
        tw = term_weight_by_entity(terms, c.tolkien_entity)
        scored.append(score_candidate(c, tw))

    merged = dedupe(scored)

    old_catalog = [Candidate(**row) for row in read_jsonl("data/catalog.jsonl")]
    old_review = [Candidate(**row) for row in read_jsonl("data/candidates.jsonl")]
    old_rejects = [Candidate(**row) for row in read_jsonl("data/rejects.jsonl")]

    reject_ids = {c.id for c in old_rejects if c.status in {"manual_rejected", "auto_rejected"}}
    existing_catalog_ids = {c.id for c in old_catalog}
    existing_review_ids = {c.id for c in old_review}

    today = date.today().isoformat()
    new_catalog = {c.id: c for c in old_catalog}
    new_review = {c.id: c for c in old_review}
    new_rejects = {c.id: c for c in old_rejects}

    for c in merged:
        if c.id in reject_ids:
            continue
        c.last_seen = today
        if c.status == "auto_accepted":
            if c.id in existing_catalog_ids:
                old = new_catalog[c.id]
                c.first_seen = old.first_seen
            new_catalog[c.id] = c
            new_review.pop(c.id, None)
        elif c.status == "needs_review":
            if c.id not in existing_catalog_ids:
                if c.id in existing_review_ids:
                    old = new_review[c.id]
                    c.first_seen = old.first_seen
                new_review[c.id] = c
        else:
            new_rejects[c.id] = c

    write_jsonl(
        "data/catalog.jsonl",
        sorted(new_catalog.values(), key=lambda x: (-x.confidence, x.name)),
    )
    write_jsonl(
        "data/candidates.jsonl",
        sorted(new_review.values(), key=lambda x: (-x.confidence, x.name)),
    )
    write_jsonl(
        "data/rejects.jsonl",
        sorted(new_rejects.values(), key=lambda x: (x.name, x.title)),
    )
    render_all()

    console.print(f"Catalog entries: {len(new_catalog)}")
    console.print(f"Review candidates: {len(new_review)}")
    console.print(f"Rejects: {len(new_rejects)}")


def promote(candidate_id: str) -> None:
    review = [Candidate(**row) for row in read_jsonl("data/candidates.jsonl")]
    catalog = [Candidate(**row) for row in read_jsonl("data/catalog.jsonl")]

    keep_review: list[Candidate] = []
    moved: Candidate | None = None
    for c in review:
        if c.id == candidate_id:
            c.status = "manual_accepted"
            moved = c
        else:
            keep_review.append(c)

    if moved is None:
        raise SystemExit(f"Candidate not found: {candidate_id}")

    catalog.append(moved)
    catalog = dedupe(catalog)
    write_jsonl("data/catalog.jsonl", catalog)
    write_jsonl("data/candidates.jsonl", keep_review)
    render_all()


def reject(candidate_id: str) -> None:
    review = [Candidate(**row) for row in read_jsonl("data/candidates.jsonl")]
    rejects = [Candidate(**row) for row in read_jsonl("data/rejects.jsonl")]

    keep_review: list[Candidate] = []
    moved: Candidate | None = None
    for c in review:
        if c.id == candidate_id:
            c.status = "manual_rejected"
            moved = c
        else:
            keep_review.append(c)

    if moved is None:
        raise SystemExit(f"Candidate not found: {candidate_id}")

    rejects.append(moved)
    write_jsonl("data/rejects.jsonl", rejects)
    write_jsonl("data/candidates.jsonl", keep_review)
    render_all()


def validate() -> None:
    for path in ["data/catalog.jsonl", "data/candidates.jsonl", "data/rejects.jsonl"]:
        rows = read_jsonl(path)
        for row in rows:
            Candidate(**row)
        console.print(f"OK: {path}: {len(rows)} rows")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(prog="lotr-index")
    sub = parser.add_subparsers(dest="command", required=True)

    sweep = sub.add_parser("sweep")
    sweep.add_argument("--days-back", type=int, default=3)
    sweep.add_argument("--source", choices=COLLECTORS, default=None)

    sub.add_parser("render")
    sub.add_parser("validate")

    promote_cmd = sub.add_parser("promote")
    promote_cmd.add_argument("--id", required=True)

    reject_cmd = sub.add_parser("reject")
    reject_cmd.add_argument("--id", required=True)

    args = parser.parse_args()
    if args.command == "sweep":
        run_sweep(days_back=args.days_back, source=args.source)
    elif args.command == "render":
        render_all()
    elif args.command == "validate":
        validate()
    elif args.command == "promote":
        promote(args.id)
    elif args.command == "reject":
        reject(args.id)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
