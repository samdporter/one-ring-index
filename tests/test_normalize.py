from lotr_index.normalize import find_acronym_expansion, normalize_text, stable_id


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
