from pathlib import Path

import pytest

from lotr_index.model import Candidate
from lotr_index.render import render_csv_json, render_markdown


def _make_candidate(**kwargs) -> Candidate:
    defaults = dict(
        id="1",
        name="GANDALF",
        source_type="paper",
        source_name="arXiv",
        title="GANDALF paper",
        artifact_type="model",
        url="https://arxiv.org/abs/0000.00000",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return Candidate(**defaults)


def test_render_creates_index_and_candidates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    c = _make_candidate()
    render_markdown([c], [])
    assert (tmp_path / "docs" / "index.md").exists()
    assert (tmp_path / "docs" / "candidates.md").exists()


def test_render_csv_json_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    c = _make_candidate()
    render_csv_json([c])
    assert (tmp_path / "docs" / "catalog.csv").exists()
    assert (tmp_path / "docs" / "catalog.json").exists()


def test_render_index_contains_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    c = _make_candidate(name="FRODO")
    render_markdown([c], [])
    content = (tmp_path / "docs" / "index.md").read_text()
    assert "FRODO" in content


def test_render_csv_empty_catalog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    render_csv_json([])
    assert (tmp_path / "docs" / "catalog.csv").exists()


def test_render_candidates_table(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    c = _make_candidate(name="SAMWISE", evidence_snippet="Some evidence here")
    render_markdown([], [c])
    content = (tmp_path / "docs" / "candidates.md").read_text()
    assert "SAMWISE" in content
