from __future__ import annotations

from .model import Candidate
from .normalize import normalize_text

SOURCE_QUALITY = {
    "arXiv": 0.90,
    "OpenAlex": 0.85,
    "Crossref": 0.85,
    "Semantic Scholar": 0.85,
    "GitHub": 0.75,
    "Hugging Face": 0.75,
    "PyPI": 0.70,
    "npm": 0.70,
    "Zenodo": 0.80,
}

MATCH_STRENGTH = {
    "full_acronym": 1.00,
    "partial_acronym": 0.80,
    "backronym": 0.75,
    "name_only": 0.65,
    "benchmark_name": 0.70,
    "dataset_name": 0.70,
    "tool_name": 0.70,
    "weak_allusion": 0.45,
    "false_positive": 0.00,
    "unknown": 0.25,
}

ML_TERMS = [
    "deep learning",
    "machine learning",
    "neural",
    "llm",
    "large language model",
    "transformer",
    "diffusion",
    "reinforcement learning",
    "computer vision",
    "natural language processing",
    "robotics",
    "benchmark",
    "dataset",
    "model",
    "software",
    "tool",
    "framework",
    "pytorch",
    "tensorflow",
]


def ml_context_strength(candidate: Candidate) -> float:
    text = normalize_text(" ".join([
        candidate.title or "",
        candidate.evidence_snippet or "",
        candidate.domain or "",
        candidate.artifact_type or "",
    ]))
    hits = sum(1 for term in ML_TERMS if term in text)
    if hits >= 3:
        return 1.0
    if hits == 2:
        return 0.8
    if hits == 1:
        return 0.55
    return 0.20


def evidence_quality(candidate: Candidate) -> float:
    if candidate.evidence_snippet and len(candidate.evidence_snippet) >= 40:
        return 1.0
    if candidate.evidence_snippet:
        return 0.6
    return 0.2


def score_candidate(candidate: Candidate, term_weight: float) -> Candidate:
    if candidate.match_kind == "false_positive":
        candidate.confidence = 0.0
        candidate.status = "auto_rejected"
        return candidate

    source_quality = SOURCE_QUALITY.get(candidate.source_name, 0.60)
    match_strength = MATCH_STRENGTH.get(candidate.match_kind, 0.25)
    ml_strength = ml_context_strength(candidate)
    ev_strength = evidence_quality(candidate)

    score = (
        0.35 * term_weight
        + 0.25 * match_strength
        + 0.20 * ml_strength
        + 0.10 * source_quality
        + 0.10 * ev_strength
    )
    candidate.confidence = round(min(max(score, 0.0), 1.0), 4)

    if candidate.confidence >= 0.85:
        candidate.status = "auto_accepted"
    elif candidate.confidence >= 0.60:
        candidate.status = "needs_review"
    else:
        candidate.status = "auto_rejected"

    return candidate
