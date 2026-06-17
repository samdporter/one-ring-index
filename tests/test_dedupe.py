from lotr_index.dedupe import dedupe, dedupe_key
from lotr_index.model import Candidate


def _make(raw_source_id: str, confidence: float = 0.5, doi: str | None = None) -> Candidate:
    return Candidate(
        id=raw_source_id,
        name="GANDALF",
        source_type="paper",
        source_name="arXiv",
        title="Same",
        url="https://arxiv.org/abs/0000.00000",
        raw_source_id=raw_source_id,
        doi=doi,
        confidence=confidence,
    )


def test_dedupe_keeps_higher_confidence():
    low = _make("arxiv:x", confidence=0.5)
    high = _make("arxiv:x", confidence=0.9)
    rows = dedupe([low, high])
    assert len(rows) == 1
    assert rows[0].confidence == 0.9


def test_dedupe_doi_takes_precedence_over_raw_source_id():
    a = _make("arxiv:x", doi="10.1234/foo")
    b = _make("other:y", doi="10.1234/foo")
    rows = dedupe([a, b])
    assert len(rows) == 1


def test_dedupe_different_keys_kept_separate():
    a = _make("arxiv:x")
    b = _make("arxiv:y")
    rows = dedupe([a, b])
    assert len(rows) == 2


def test_dedupe_sorted_by_confidence_desc():
    a = _make("arxiv:x", confidence=0.7)
    b = _make("arxiv:y", confidence=0.9)
    rows = dedupe([a, b])
    assert rows[0].confidence == 0.9
