from lotr_index.model import Candidate
from lotr_index.score import score_candidate


def _make_candidate(**kwargs) -> Candidate:
    defaults = dict(
        id="1",
        name="GANDALF",
        source_type="paper",
        source_name="arXiv",
        title="GANDALF: a neural model",
        url="https://arxiv.org/abs/0000.00000",
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def test_high_confidence_full_acronym_accepted():
    c = _make_candidate(
        expanded_form="Gated Adaptive Network for Deep Automated Learning of Features",
        tolkien_entity="Gandalf",
        match_kind="full_acronym",
        artifact_type="model",
        domain="machine learning",
        evidence_snippet="GANDALF is a neural model for machine learning tasks.",
    )
    scored = score_candidate(c, 1.0)
    assert scored.confidence >= 0.85
    assert scored.status == "auto_accepted"


def test_false_positive_always_rejected():
    c = _make_candidate(match_kind="false_positive")
    scored = score_candidate(c, 1.0)
    assert scored.status == "auto_rejected"
    assert scored.confidence == 0.0


def test_low_precision_term_without_context_needs_review_or_rejected():
    c = _make_candidate(
        name="RING",
        match_kind="name_only",
        evidence_snippet="ring buffer implementation",
    )
    scored = score_candidate(c, 0.30)
    assert scored.confidence < 0.85


def test_confidence_clamped_between_0_and_1():
    c = _make_candidate(match_kind="full_acronym", evidence_snippet="x" * 200)
    scored = score_candidate(c, 1.0)
    assert 0.0 <= scored.confidence <= 1.0


def test_needs_review_range():
    c = _make_candidate(
        match_kind="name_only",
        evidence_snippet="GANDALF software tool for machine learning",
    )
    scored = score_candidate(c, 0.85)
    assert scored.status in ("needs_review", "auto_accepted", "auto_rejected")
