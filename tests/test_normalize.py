from lotr_index.normalize import evidence_window, find_acronym_expansion, normalize_text, stable_id


def test_normalize_text_removes_extra_space():
    assert normalize_text("  GANDALF   Model ") == "gandalf model"


def test_normalize_text_strips_combining_chars():
    assert normalize_text("café") == "cafe"


def test_stable_id_stable():
    assert stable_id("a", "b") == stable_id("a", "b")


def test_stable_id_different_inputs_differ():
    assert stable_id("a", "b") != stable_id("a", "c")


def test_stable_id_none_safe():
    assert stable_id(None, "b") == stable_id(None, "b")


def test_find_acronym_expansion():
    text = "GANDALF: Gated Adaptive Network for Deep Automated Learning of Features"
    result = find_acronym_expansion(text, "GANDALF")
    assert result is not None
    assert result.startswith("Gated Adaptive")


def test_find_acronym_expansion_missing():
    assert find_acronym_expansion("some unrelated text", "GANDALF") is None


def test_find_acronym_expansion_none_text():
    assert find_acronym_expansion(None, "GANDALF") is None


def test_evidence_window_finds_term():
    text = "Some text here and then GANDALF appears in the middle of a sentence."
    result = evidence_window(text, "GANDALF")
    assert result is not None
    assert "GANDALF" in result


def test_evidence_window_returns_none_when_not_found():
    assert evidence_window("no match here", "GANDALF") is None


def test_evidence_window_handles_none_text():
    assert evidence_window(None, "GANDALF") is None
