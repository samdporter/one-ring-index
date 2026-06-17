from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .model import Candidate


def ensure_dirs() -> None:
    for path in ["data", "data/raw", "data/cache", "docs"]:
        Path(path).mkdir(parents=True, exist_ok=True)


def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: Iterable[dict | Candidate]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            if isinstance(row, Candidate):
                payload = row.model_dump(mode="json")
            else:
                payload = row
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
