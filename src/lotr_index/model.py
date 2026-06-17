from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

MatchKind = Literal[
    "full_acronym",
    "partial_acronym",
    "backronym",
    "name_only",
    "benchmark_name",
    "dataset_name",
    "tool_name",
    "weak_allusion",
    "false_positive",
    "unknown",
]

ArtifactType = Literal[
    "model",
    "method",
    "benchmark",
    "dataset",
    "tool",
    "library",
    "package",
    "repository",
    "paper",
    "software",
    "unknown",
]

Status = Literal[
    "auto_accepted",
    "needs_review",
    "manual_accepted",
    "manual_rejected",
    "auto_rejected",
]


class Candidate(BaseModel):
    id: str
    name: str
    expanded_form: str | None = None
    tolkien_entity: str | None = None
    match_kind: MatchKind = "unknown"
    artifact_type: ArtifactType = "unknown"
    domain: str | None = None
    source_type: str
    source_name: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    published_date: str | None = None
    updated_date: str | None = None
    url: HttpUrl | str
    doi: str | None = None
    repo: str | None = None
    package_name: str | None = None
    evidence_snippet: str | None = None
    confidence: float = 0.0
    status: Status = "needs_review"
    first_seen: str = Field(default_factory=lambda: date.today().isoformat())
    last_seen: str = Field(default_factory=lambda: date.today().isoformat())
    raw_source_id: str | None = None
