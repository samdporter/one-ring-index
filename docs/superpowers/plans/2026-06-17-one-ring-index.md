# One Ring Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub-hosted Python workspace that automatically runs a daily search across arXiv, GitHub, Hugging Face, PyPI, npm, Zenodo, OpenAlex, Crossref, and Semantic Scholar to maintain a deduplicated, scored, and human-readable catalog of Tolkien/LOTR-inspired names used in AI models, benchmarks, datasets, tools, and software.

**Architecture:** A CLI tool (`lotr-index`) reads Tolkien term config YAMLs, dispatches per-source collectors that return `Candidate` Pydantic models, scores and deduplicates the results, and writes JSON Lines catalog/candidate/reject files plus rendered Markdown, CSV, and JSON under `docs/`. A daily GitHub Actions workflow runs the full sweep and commits the output files.

**Tech Stack:** Python 3.12, Pydantic v2, httpx, feedparser, rapidfuzz, huggingface_hub, PyYAML, rich, argparse, pytest, ruff

## Global Constraints

- Python >= 3.12
- All source under `src/lotr_index/` (setuptools src layout)
- CLI entry point: `lotr-index` → `lotr_index.cli:main`
- Three data stores: `data/catalog.jsonl`, `data/candidates.jsonl`, `data/rejects.jsonl`
- Docs rendered to `docs/index.md`, `docs/candidates.md`, `docs/catalog.csv`, `docs/catalog.json`
- Cache responses under `data/cache/<namespace>/`
- User-Agent must include `one-ring-index/0.1 (mailto:<CONTACT_EMAIL>)`
- arXiv: minimum 3-second delay between live requests
- GitHub REST: honor 429/500/502/503/504 with exponential backoff; use `GITHUB_TOKEN` env var
- Crossref: include `mailto` query param from `CONTACT_EMAIL` env var
- OpenAlex: skip cleanly if `OPENALEX_API_KEY` not set
- Semantic Scholar: minimum 1.1-second delay per request; use `SEMANTIC_SCHOLAR_API_KEY` if set
- Hugging Face: use `huggingface_hub.HfApi`; use `HF_TOKEN` if set
- No PDF downloading, no full-text mirroring, no browser automation, no uncontrolled crawling
- `status` values: `auto_accepted`, `needs_review`, `manual_accepted`, `manual_rejected`, `auto_rejected`
- Auto-accept threshold: confidence >= 0.85; needs-review: 0.60–0.85; auto-reject: < 0.60
- Scheduled cron: `17 3 * * *` (odd minute, avoids top-of-hour load)

---

## File Map

**Created files (new project):**

```
one-ring-index/
  .gitignore
  .env.example
  LICENSE
  pyproject.toml
  README.md
  .devcontainer/devcontainer.json
  .github/workflows/daily-sweep.yml
  config/tolkien_terms.yml
  config/source_queries.yml
  config/negative_terms.yml
  src/lotr_index/__init__.py
  src/lotr_index/model.py          # Candidate Pydantic model + type literals
  src/lotr_index/storage.py        # read_jsonl / write_jsonl / ensure_dirs
  src/lotr_index/normalize.py      # normalize_text, stable_id, find_acronym_expansion, evidence_window
  src/lotr_index/http.py           # get_json with caching + retry
  src/lotr_index/logging_config.py # configure_logging()
  src/lotr_index/score.py          # score_candidate() — sets confidence + status
  src/lotr_index/dedupe.py         # dedupe() — keeps highest confidence per key
  src/lotr_index/render.py         # render_markdown, render_csv_json, render_all
  src/lotr_index/collectors/__init__.py
  src/lotr_index/collectors/arxiv.py
  src/lotr_index/collectors/github.py
  src/lotr_index/collectors/huggingface.py
  src/lotr_index/collectors/openalex.py
  src/lotr_index/collectors/crossref.py
  src/lotr_index/collectors/semantic_scholar.py
  src/lotr_index/collectors/pypi.py
  src/lotr_index/collectors/npm.py
  src/lotr_index/collectors/zenodo.py
  tests/test_normalize.py
  tests/test_score.py
  tests/test_dedupe.py
  tests/test_render.py
  data/raw/.gitkeep
  data/cache/.gitkeep
  data/catalog.jsonl
  data/candidates.jsonl
  data/rejects.jsonl
  docs/superpowers/plans/2026-06-17-one-ring-index.md   ← this file
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `LICENSE`
- Create: `.devcontainer/devcontainer.json`
- Create: `config/tolkien_terms.yml`
- Create: `config/source_queries.yml`
- Create: `config/negative_terms.yml`
- Create: `src/lotr_index/__init__.py`
- Create: `src/lotr_index/collectors/__init__.py`
- Create: `data/raw/.gitkeep`, `data/cache/.gitkeep`
- Create: `data/catalog.jsonl`, `data/candidates.jsonl`, `data/rejects.jsonl` (empty)

**Interfaces:**
- Produces: installable package `lotr-index` at version `0.1.0`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p .github/workflows .devcontainer config \
         src/lotr_index/collectors tests \
         data/raw data/cache docs
touch data/raw/.gitkeep data/cache/.gitkeep \
      data/catalog.jsonl data/candidates.jsonl data/rejects.jsonl
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "lotr-index"
version = "0.1.0"
description = "Daily index of Tolkien-inspired acronyms, models, benchmarks, datasets, and software tools."
requires-python = ">=3.12"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "LOTR Index Maintainers" }]
dependencies = [
  "httpx>=0.27",
  "pydantic>=2.7",
  "python-dateutil>=2.9",
  "pyyaml>=6.0",
  "rapidfuzz>=3.9",
  "feedparser>=6.0",
  "rich>=13.7",
  "huggingface_hub>=0.24"
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "ruff>=0.5",
  "mypy>=1.10"
]

[project.scripts]
lotr-index = "lotr_index.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
.DS_Store

# Runtime scratch files
*.tmp
*.bak
```

- [ ] **Step 4: Write `.env.example`**

```dotenv
# Required for polite API access where supported.
CONTACT_EMAIL=you@example.com

# GitHub Actions provides GITHUB_TOKEN automatically.
# For local runs, use a fine-scoped token if GitHub search limits are too low.
GITHUB_TOKEN=

# Optional but recommended.
OPENALEX_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
HF_TOKEN=
ZENODO_TOKEN=
```

- [ ] **Step 5: Write `LICENSE` (MIT)**

```
MIT License

Copyright (c) 2026 LOTR Index Maintainers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 6: Write `.devcontainer/devcontainer.json`**

```json
{
  "name": "one-ring-index",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "postCreateCommand": "python -m pip install -U pip && pip install -e .[dev]",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "charliermarsh.ruff"
      ]
    }
  }
}
```

- [ ] **Step 7: Write `config/tolkien_terms.yml`**

```yaml
high_precision:
  gandalf:
    entity: "Gandalf"
    weight: 1.00
    aliases: ["gandalf"]
  frodo:
    entity: "Frodo"
    weight: 1.00
    aliases: ["frodo"]
  samwise:
    entity: "Samwise Gamgee"
    weight: 1.00
    aliases: ["samwise", "sam"]
  legolas:
    entity: "Legolas"
    weight: 1.00
    aliases: ["legolas"]
  gimli:
    entity: "Gimli"
    weight: 1.00
    aliases: ["gimli"]
  gollum:
    entity: "Gollum"
    weight: 1.00
    aliases: ["gollum", "smeagol", "sméagol"]
  sauron:
    entity: "Sauron"
    weight: 1.00
    aliases: ["sauron"]
  saruman:
    entity: "Saruman"
    weight: 1.00
    aliases: ["saruman"]
  aragorn:
    entity: "Aragorn"
    weight: 1.00
    aliases: ["aragorn", "strider"]
  rivendell:
    entity: "Rivendell"
    weight: 1.00
    aliases: ["rivendell"]
  mordor:
    entity: "Mordor"
    weight: 1.00
    aliases: ["mordor"]
  balrog:
    entity: "Balrog"
    weight: 0.95
    aliases: ["balrog"]
  mithril:
    entity: "Mithril"
    weight: 0.95
    aliases: ["mithril"]
  palantir:
    entity: "Palantír"
    weight: 0.95
    aliases: ["palantir", "palantír"]
  silmaril:
    entity: "Silmaril"
    weight: 0.95
    aliases: ["silmaril", "silmarils"]

medium_precision:
  bilbo:
    entity: "Bilbo Baggins"
    weight: 0.85
    aliases: ["bilbo"]
  arwen:
    entity: "Arwen"
    weight: 0.85
    aliases: ["arwen"]
  elrond:
    entity: "Elrond"
    weight: 0.85
    aliases: ["elrond"]
  galadriel:
    entity: "Galadriel"
    weight: 0.85
    aliases: ["galadriel"]
  rohan:
    entity: "Rohan"
    weight: 0.80
    aliases: ["rohan"]
  gondor:
    entity: "Gondor"
    weight: 0.80
    aliases: ["gondor"]
  shire:
    entity: "The Shire"
    weight: 0.70
    aliases: ["shire", "the shire"]

low_precision:
  ring:
    entity: "The One Ring"
    weight: 0.30
    aliases: ["ring", "one ring", "the one ring"]
  orc:
    entity: "Orc"
    weight: 0.25
    aliases: ["orc", "orcs"]
  elf:
    entity: "Elf"
    weight: 0.20
    aliases: ["elf", "elves", "elven"]
  ent:
    entity: "Ent"
    weight: 0.20
    aliases: ["ent", "ents"]

confirmation_terms:
  - "lord of the rings"
  - "lotr"
  - "tolkien"
  - "middle-earth"
  - "middle earth"
  - "hobbit"
  - "shire"
  - "mordor"
  - "one ring"
  - "fellowship"
```

- [ ] **Step 8: Write `config/source_queries.yml`**

```yaml
ml_context_terms:
  - "deep learning"
  - "machine learning"
  - "neural"
  - "neural network"
  - "LLM"
  - "large language model"
  - "transformer"
  - "diffusion"
  - "reinforcement learning"
  - "computer vision"
  - "natural language processing"
  - "robotics"
  - "benchmark"
  - "dataset"
  - "model"
  - "software"
  - "tool"
  - "framework"

query_templates:
  scholarly:
    - "{term} machine learning"
    - "{term} deep learning"
    - "{term} neural network"
    - "{term} LLM"
    - "{term} benchmark"
    - "{term} dataset"
    - "{term} software"
  code:
    - "{term} machine learning"
    - "{term} deep learning"
    - "{term} neural network"
    - "{term} LLM"
    - "{term} benchmark"
    - "{term} dataset"
    - "{term} software"
    - "{term} python"
    - "{term} pytorch"
    - "{term} tensorflow"
  package:
    - "{term}"
```

- [ ] **Step 9: Write `config/negative_terms.yml`**

```yaml
negative_context_terms:
  - "wedding ring"
  - "ring road"
  - "ring buffer"
  - "ring oscillator"
  - "ring signature"
  - "ring topology"
  - "orc file"
  - "apache orc"
  - "orc format"
  - "elf binary"
  - "elf file"
  - "executable and linkable format"
  - "ear nose throat"
  - "entropy"
  - "enterprise"
  - "shire county"
  - "palantir technologies"

hard_reject_domains:
  - "example.com"
```

- [ ] **Step 10: Write `src/lotr_index/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 11: Write `src/lotr_index/collectors/__init__.py`** (empty)

```python
```

- [ ] **Step 12: Create venv and install**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .[dev]
```

- [ ] **Step 13: Verify install**

```bash
python -c "import lotr_index; print(lotr_index.__version__)"
```

Expected output: `0.1.0`

- [ ] **Step 14: Commit scaffold**

```bash
git init
git add .
git commit -m "feat: scaffold one-ring-index project"
```

---

### Task 2: Core Library — Model, Storage, Normalize, HTTP, Logging

**Files:**
- Create: `src/lotr_index/model.py`
- Create: `src/lotr_index/storage.py`
- Create: `src/lotr_index/normalize.py`
- Create: `src/lotr_index/http.py`
- Create: `src/lotr_index/logging_config.py`
- Create: `tests/test_normalize.py`

**Interfaces:**
- Produces:
  - `Candidate` Pydantic model with fields: `id`, `name`, `expanded_form`, `tolkien_entity`, `match_kind`, `artifact_type`, `domain`, `source_type`, `source_name`, `title`, `authors`, `year`, `published_date`, `updated_date`, `url`, `doi`, `repo`, `package_name`, `evidence_snippet`, `confidence`, `status`, `first_seen`, `last_seen`, `raw_source_id`
  - `read_jsonl(path) -> list[dict]`
  - `write_jsonl(path, rows)` — accepts `Candidate` or `dict`
  - `ensure_dirs()`
  - `normalize_text(text) -> str`
  - `stable_id(*parts) -> str`
  - `find_acronym_expansion(text, name) -> str | None`
  - `evidence_window(text, term, width=180) -> str | None`
  - `get_json(url, *, params, headers, cache_namespace, min_delay_seconds, use_cache) -> dict`
  - `configure_logging()`

- [ ] **Step 1: Write `tests/test_normalize.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_normalize.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — normalize module doesn't exist yet.

- [ ] **Step 3: Write `src/lotr_index/normalize.py`**

```python
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

ACRONYM_EXPANSION_RE = re.compile(
    r"\b([A-Z][A-Z0-9]{2,16})\b\s*(?:[:=\-–—]|\(|,)\s*([A-Z][^\.\n]{8,240})",
    re.MULTILINE,
)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def stable_id(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def find_acronym_expansion(text: str | None, name: str) -> str | None:
    if not text:
        return None
    target = name.upper()
    for match in ACRONYM_EXPANSION_RE.finditer(text):
        acronym = match.group(1).upper()
        expansion = match.group(2).strip()
        if acronym == target:
            return expansion
    return None


def evidence_window(text: str | None, term: str, width: int = 180) -> str | None:
    if not text or not term:
        return None
    low = text.lower()
    idx = low.find(term.lower())
    if idx == -1:
        return None
    start = max(0, idx - width)
    end = min(len(text), idx + len(term) + width)
    snippet = text[start:end]
    return re.sub(r"\s+", " ", snippet).strip()
```

- [ ] **Step 4: Run normalize tests — must pass**

```bash
pytest tests/test_normalize.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Write `src/lotr_index/model.py`**

```python
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
```

- [ ] **Step 6: Write `src/lotr_index/storage.py`**

```python
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
```

- [ ] **Step 7: Write `src/lotr_index/http.py`**

```python
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

DEFAULT_TIMEOUT = 30.0


def _cache_key(method: str, url: str, params: dict[str, Any] | None) -> str:
    payload = json.dumps({"method": method, "url": url, "params": params or {}}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    cache_namespace: str = "default",
    min_delay_seconds: float = 0.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    contact = os.getenv("CONTACT_EMAIL", "unknown@example.com")
    merged_headers = {
        "User-Agent": f"one-ring-index/0.1 (mailto:{contact})",
        "Accept": "application/json",
    }
    if headers:
        merged_headers.update(headers)

    cache_dir = Path("data/cache") / cache_namespace
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key("GET", url, params)
    cache_path = cache_dir / f"{key}.json"

    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if min_delay_seconds > 0:
        time.sleep(min_delay_seconds)

    for attempt in range(5):
        try:
            response = httpx.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("unreachable")
```

- [ ] **Step 8: Write `src/lotr_index/logging_config.py`**

```python
from __future__ import annotations

import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
```

- [ ] **Step 9: Verify model imports correctly**

```bash
python -c "from lotr_index.model import Candidate; c = Candidate(id='x', name='GANDALF', source_type='paper', source_name='arXiv', title='Test', url='https://arxiv.org/abs/0'); print(c.status)"
```

Expected output: `needs_review`

- [ ] **Step 10: Commit core library**

```bash
git add src/lotr_index/model.py src/lotr_index/storage.py src/lotr_index/normalize.py \
        src/lotr_index/http.py src/lotr_index/logging_config.py tests/test_normalize.py
git commit -m "feat: add core library — model, storage, normalize, http, logging"
```

---

### Task 3: Scoring and Deduplication

**Files:**
- Create: `src/lotr_index/score.py`
- Create: `src/lotr_index/dedupe.py`
- Create: `tests/test_score.py`
- Create: `tests/test_dedupe.py`

**Interfaces:**
- Consumes: `Candidate` from `lotr_index.model`; `normalize_text` from `lotr_index.normalize`
- Produces:
  - `score_candidate(candidate: Candidate, term_weight: float) -> Candidate` — mutates and returns candidate with `confidence` and `status` set
  - `dedupe(candidates: list[Candidate]) -> list[Candidate]` — returns highest-confidence winner per dedupe key, sorted by `-confidence, name, title`
  - `dedupe_key(c: Candidate) -> str`

- [ ] **Step 1: Write `tests/test_score.py`**

```python
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
```

- [ ] **Step 2: Write `tests/test_dedupe.py`**

```python
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
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_score.py tests/test_dedupe.py -v
```

Expected: `ImportError` — modules don't exist yet.

- [ ] **Step 4: Write `src/lotr_index/score.py`**

```python
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
```

- [ ] **Step 5: Write `src/lotr_index/dedupe.py`**

```python
from __future__ import annotations

from .model import Candidate
from .normalize import normalize_text


def dedupe_key(c: Candidate) -> str:
    if c.doi:
        return f"doi:{normalize_text(c.doi)}"
    if c.raw_source_id:
        return f"raw:{normalize_text(c.raw_source_id)}"
    if c.repo:
        return f"repo:{normalize_text(c.repo)}"
    if c.package_name and c.source_name:
        return f"pkg:{normalize_text(c.source_name)}:{normalize_text(c.package_name)}"
    return f"title:{normalize_text(c.title)}:{normalize_text(str(c.url))}"


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    best: dict[str, Candidate] = {}
    for c in candidates:
        key = dedupe_key(c)
        old = best.get(key)
        if old is None or c.confidence > old.confidence:
            best[key] = c
    return sorted(
        best.values(),
        key=lambda x: (-x.confidence, x.name.lower(), x.title.lower()),
    )
```

- [ ] **Step 6: Run scoring and dedupe tests — must pass**

```bash
pytest tests/test_score.py tests/test_dedupe.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/lotr_index/score.py src/lotr_index/dedupe.py \
        tests/test_score.py tests/test_dedupe.py
git commit -m "feat: add scoring and deduplication"
```

---

### Task 4: Render Module

**Files:**
- Create: `src/lotr_index/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `Candidate` from `lotr_index.model`; `read_jsonl` from `lotr_index.storage`
- Produces:
  - `render_markdown(catalog: list[Candidate], candidates: list[Candidate]) -> None` — writes `docs/index.md` and `docs/candidates.md`
  - `render_csv_json(catalog: list[Candidate]) -> None` — writes `docs/catalog.csv` and `docs/catalog.json`
  - `render_all() -> None` — loads from `data/catalog.jsonl` + `data/candidates.jsonl`, calls both renderers

- [ ] **Step 1: Write `tests/test_render.py`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_render.py -v
```

Expected: `ImportError` — render module doesn't exist.

- [ ] **Step 3: Write `src/lotr_index/render.py`**

```python
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
```

- [ ] **Step 4: Run render tests — must pass**

```bash
pytest tests/test_render.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/lotr_index/render.py tests/test_render.py
git commit -m "feat: add render module"
```

---

### Task 5: Collectors

**Files:**
- Create: `src/lotr_index/collectors/arxiv.py`
- Create: `src/lotr_index/collectors/github.py`
- Create: `src/lotr_index/collectors/huggingface.py`
- Create: `src/lotr_index/collectors/openalex.py`
- Create: `src/lotr_index/collectors/crossref.py`
- Create: `src/lotr_index/collectors/semantic_scholar.py`
- Create: `src/lotr_index/collectors/pypi.py`
- Create: `src/lotr_index/collectors/npm.py`
- Create: `src/lotr_index/collectors/zenodo.py`

**Interfaces:**
- Consumes: `Candidate` from `lotr_index.model`; `get_json` from `lotr_index.http`; `evidence_window`, `find_acronym_expansion`, `stable_id` from `lotr_index.normalize`
- Produces: each module exposes `collect(terms: dict, days_back: int = 3, max_results: int = 50) -> list[Candidate]`
  - All collectors catch their own errors and return `[]` on source failure (never crash the whole run)
  - OpenAlex, Semantic Scholar: return `[]` and log warning if required env var not set

- [ ] **Step 1: Write `src/lotr_index/collectors/arxiv.py`**

```python
from __future__ import annotations

import logging
import os
import time
from urllib.parse import urlencode

import feedparser
import httpx

from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"


def _guess_artifact_type(text: str) -> str:
    low = text.lower()
    if "benchmark" in low:
        return "benchmark"
    if "dataset" in low:
        return "dataset"
    if "model" in low:
        return "model"
    if "software" in low or "tool" in low or "framework" in low:
        return "tool"
    return "paper"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    results: list[Candidate] = []
    contact = os.getenv("CONTACT_EMAIL", "unknown@example.com")
    headers = {"User-Agent": f"one-ring-index/0.1 (mailto:{contact})"}

    for key, meta in terms.items():
        aliases = meta.get("aliases", [key])
        for alias in aliases[:2]:
            query = (
                f'all:"{alias}" AND ('
                'all:"machine learning" OR all:"deep learning" OR all:"neural" '
                'OR all:"LLM" OR all:"benchmark" OR all:"dataset" OR all:"software")'
            )
            params = {
                "search_query": query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending",
            }
            url = f"{ARXIV_API}?{urlencode(params)}"
            try:
                time.sleep(3.1)
                response = httpx.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
            except Exception as exc:
                log.warning("arXiv query failed for %s: %s", alias, exc)
                continue

            for entry in feed.entries:
                title = entry.get("title", "").replace("\n", " ").strip()
                summary = entry.get("summary", "").replace("\n", " ").strip()
                text = f"{title}. {summary}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                match_kind = "full_acronym" if expansion else "name_only"
                arxiv_id = entry.get("id", "")
                authors = [a.get("name", "") for a in entry.get("authors", [])]
                published = entry.get("published", "")[:10] or None
                year = int(published[:4]) if published and published[:4].isdigit() else None

                results.append(Candidate(
                    id=stable_id("arxiv", arxiv_id, alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind=match_kind,
                    artifact_type=_guess_artifact_type(text),
                    domain="machine learning / software",
                    source_type="paper",
                    source_name="arXiv",
                    title=title,
                    authors=authors,
                    year=year,
                    published_date=published,
                    updated_date=entry.get("updated", "")[:10] or None,
                    url=arxiv_id or entry.get("link", "https://arxiv.org"),
                    evidence_snippet=snippet,
                    raw_source_id=f"arxiv:{arxiv_id}",
                ))
    return results
```

- [ ] **Step 2: Write `src/lotr_index/collectors/github.py`**

```python
from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)

GITHUB_SEARCH_REPOS = "https://api.github.com/search/repositories"


def _guess_artifact_type(text: str) -> str:
    low = text.lower()
    if "dataset" in low:
        return "dataset"
    if "benchmark" in low:
        return "benchmark"
    if "model" in low or "llm" in low:
        return "model"
    if "library" in low:
        return "library"
    return "repository"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    token = os.getenv("GITHUB_TOKEN")
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    results: list[Candidate] = []
    for key, meta in terms.items():
        aliases = meta.get("aliases", [key])
        for alias in aliases[:2]:
            q = (
                f"{alias} machine-learning OR deep-learning OR LLM OR neural "
                "OR benchmark OR dataset in:name,description,readme"
            )
            params = {"q": q, "sort": "updated", "order": "desc", "per_page": max_results}
            try:
                data = get_json(
                    GITHUB_SEARCH_REPOS,
                    params=params,
                    headers=headers,
                    cache_namespace="github",
                )
            except Exception as exc:
                log.warning("GitHub query failed for %s: %s", alias, exc)
                continue

            for item in data.get("items", []):
                title = item.get("full_name") or item.get("name") or "unknown"
                desc = item.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("github", item.get("html_url"), alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="name_only",
                    artifact_type=_guess_artifact_type(text),
                    domain="software",
                    source_type="repository",
                    source_name="GitHub",
                    title=title,
                    authors=[item.get("owner", {}).get("login", "")],
                    published_date=item.get("created_at", "")[:10] or None,
                    updated_date=item.get("updated_at", "")[:10] or None,
                    url=item.get("html_url") or "https://github.com",
                    repo=item.get("full_name"),
                    evidence_snippet=snippet,
                    raw_source_id=f"github:{item.get('id')}",
                ))
    return results
```

- [ ] **Step 3: Write `src/lotr_index/collectors/huggingface.py`**

```python
from __future__ import annotations

import logging
import os

from huggingface_hub import HfApi

from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    api = HfApi(token=os.getenv("HF_TOKEN") or None)
    results: list[Candidate] = []

    for key, meta in terms.items():
        aliases = meta.get("aliases", [key])
        for alias in aliases[:2]:
            try:
                models = list(api.list_models(search=alias, limit=max_results))
            except Exception as exc:
                log.warning("Hugging Face model query failed for %s: %s", alias, exc)
                models = []
            for m in models:
                model_id = getattr(m, "modelId", None) or getattr(m, "id", None)
                if not model_id:
                    continue
                snippet = evidence_window(model_id, alias) or model_id
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("huggingface-model", model_id, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="name_only",
                    artifact_type="model",
                    domain="machine learning",
                    source_type="model_hub",
                    source_name="Hugging Face",
                    title=model_id,
                    url=f"https://huggingface.co/{model_id}",
                    evidence_snippet=snippet,
                    raw_source_id=f"hf:model:{model_id}",
                ))

            try:
                datasets = list(api.list_datasets(search=alias, limit=max_results))
            except Exception as exc:
                log.warning("Hugging Face dataset query failed for %s: %s", alias, exc)
                datasets = []
            for d in datasets:
                dataset_id = getattr(d, "id", None)
                if not dataset_id:
                    continue
                snippet = evidence_window(dataset_id, alias) or dataset_id
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("huggingface-dataset", dataset_id, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="dataset_name",
                    artifact_type="dataset",
                    domain="machine learning",
                    source_type="dataset_hub",
                    source_name="Hugging Face",
                    title=dataset_id,
                    url=f"https://huggingface.co/datasets/{dataset_id}",
                    evidence_snippet=snippet,
                    raw_source_id=f"hf:dataset:{dataset_id}",
                ))
    return results
```

- [ ] **Step 4: Write `src/lotr_index/collectors/openalex.py`**

```python
from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

OPENALEX_WORKS = "https://api.openalex.org/works"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    api_key = os.getenv("OPENALEX_API_KEY")
    if not api_key:
        log.info("OPENALEX_API_KEY not set; skipping OpenAlex")
        return []

    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "search": f"{alias} machine learning deep learning neural software benchmark dataset",
                "per-page": min(max_results, 25),
                "api_key": api_key,
            }
            try:
                data = get_json(OPENALEX_WORKS, params=params, cache_namespace="openalex")
            except Exception as exc:
                log.warning("OpenAlex query failed for %s: %s", alias, exc)
                continue
            for item in data.get("results", []):
                title = item.get("title") or "unknown"
                text = title
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                results.append(Candidate(
                    id=stable_id("openalex", item.get("id"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="OpenAlex",
                    title=title,
                    year=item.get("publication_year"),
                    published_date=item.get("publication_date"),
                    url=item.get("doi") or item.get("id") or "https://openalex.org",
                    doi=item.get("doi"),
                    evidence_snippet=snippet,
                    raw_source_id=f"openalex:{item.get('id')}",
                ))
    return results
```

- [ ] **Step 5: Write `src/lotr_index/collectors/crossref.py`**

```python
from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

CROSSREF_WORKS = "https://api.crossref.org/works"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    contact = os.getenv("CONTACT_EMAIL", "unknown@example.com")
    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "query.bibliographic": (
                    f"{alias} machine learning deep learning neural software benchmark dataset"
                ),
                "rows": min(max_results, 20),
                "mailto": contact,
            }
            try:
                data = get_json(CROSSREF_WORKS, params=params, cache_namespace="crossref")
            except Exception as exc:
                log.warning("Crossref query failed for %s: %s", alias, exc)
                continue
            for item in data.get("message", {}).get("items", []):
                title = " ".join(item.get("title", [])[:1]) or "unknown"
                text = title
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                doi = item.get("DOI")
                results.append(Candidate(
                    id=stable_id("crossref", doi or item.get("URL"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="Crossref",
                    title=title,
                    url=item.get("URL") or (f"https://doi.org/{doi}" if doi else "https://www.crossref.org"),
                    doi=doi,
                    evidence_snippet=snippet,
                    raw_source_id=f"crossref:{doi}",
                ))
    return results
```

- [ ] **Step 6: Write `src/lotr_index/collectors/semantic_scholar.py`**

```python
from __future__ import annotations

import logging
import os

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    headers: dict[str, str] = {}
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if key:
        headers["x-api-key"] = key

    results: list[Candidate] = []
    for term_key, meta in terms.items():
        for alias in meta.get("aliases", [term_key])[:2]:
            params = {
                "query": f"{alias} machine learning deep learning neural software benchmark dataset",
                "limit": min(max_results, 20),
                "fields": "title,abstract,authors,year,url,externalIds,publicationDate",
            }
            try:
                data = get_json(
                    S2_SEARCH,
                    params=params,
                    headers=headers,
                    cache_namespace="semantic_scholar",
                    min_delay_seconds=1.1,
                )
            except Exception as exc:
                log.warning("Semantic Scholar query failed for %s: %s", alias, exc)
                continue
            for item in data.get("data", []):
                title = item.get("title") or "unknown"
                abstract = item.get("abstract") or ""
                text = f"{title}. {abstract}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                authors = [a.get("name", "") for a in item.get("authors", [])]
                doi = (item.get("externalIds") or {}).get("DOI")
                results.append(Candidate(
                    id=stable_id("semantic_scholar", item.get("paperId"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type="paper",
                    domain="scholarly metadata",
                    source_type="paper",
                    source_name="Semantic Scholar",
                    title=title,
                    authors=authors,
                    year=item.get("year"),
                    published_date=item.get("publicationDate"),
                    url=item.get("url") or "https://www.semanticscholar.org/",
                    doi=doi,
                    evidence_snippet=snippet,
                    raw_source_id=f"s2:{item.get('paperId')}",
                ))
    return results
```

- [ ] **Step 7: Write `src/lotr_index/collectors/pypi.py`**

```python
from __future__ import annotations

import logging

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back, max_results
    results: list[Candidate] = []
    variants = ["", "-ml", "-ai", "-torch", "-pytorch", "-llm"]

    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            for suffix in variants:
                package = f"{alias.lower()}{suffix}"
                url = f"https://pypi.org/pypi/{package}/json"
                try:
                    data = get_json(url, cache_namespace="pypi")
                except Exception:
                    continue
                info = data.get("info", {})
                title = info.get("name") or package
                summary = info.get("summary") or ""
                project_url = info.get("project_url") or f"https://pypi.org/project/{package}/"
                text = f"{title}. {summary}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("pypi", package, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="tool_name",
                    artifact_type="package",
                    domain="software package",
                    source_type="package_registry",
                    source_name="PyPI",
                    title=title,
                    url=project_url,
                    package_name=package,
                    evidence_snippet=snippet,
                    raw_source_id=f"pypi:{package}",
                ))
    return results
```

- [ ] **Step 8: Write `src/lotr_index/collectors/npm.py`**

```python
from __future__ import annotations

import logging
from urllib.parse import quote

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)

NPM_REGISTRY = "https://registry.npmjs.org"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back, max_results
    results: list[Candidate] = []
    variants = ["", "-ml", "-ai", "-llm", "-js"]

    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            for suffix in variants:
                package = f"{alias.lower()}{suffix}"
                url = f"{NPM_REGISTRY}/{quote(package)}"
                try:
                    data = get_json(url, cache_namespace="npm")
                except Exception:
                    continue
                title = data.get("name") or package
                desc = data.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                results.append(Candidate(
                    id=stable_id("npm", package, alias),
                    name=name,
                    tolkien_entity=meta.get("entity"),
                    match_kind="tool_name",
                    artifact_type="package",
                    domain="software package",
                    source_type="package_registry",
                    source_name="npm",
                    title=title,
                    url=f"https://www.npmjs.com/package/{package}",
                    package_name=package,
                    evidence_snippet=snippet,
                    raw_source_id=f"npm:{package}",
                ))
    return results
```

- [ ] **Step 9: Write `src/lotr_index/collectors/zenodo.py`**

```python
from __future__ import annotations

import logging

from ..http import get_json
from ..model import Candidate
from ..normalize import evidence_window, find_acronym_expansion, stable_id

log = logging.getLogger(__name__)

ZENODO_RECORDS = "https://zenodo.org/api/records"


def collect(terms: dict, days_back: int = 3, max_results: int = 20) -> list[Candidate]:
    del days_back
    results: list[Candidate] = []
    for key, meta in terms.items():
        for alias in meta.get("aliases", [key])[:2]:
            params = {
                "q": f"{alias} machine learning deep learning neural software benchmark dataset",
                "size": min(max_results, 20),
                "sort": "mostrecent",
            }
            try:
                data = get_json(ZENODO_RECORDS, params=params, cache_namespace="zenodo")
            except Exception as exc:
                log.warning("Zenodo query failed for %s: %s", alias, exc)
                continue
            for item in data.get("hits", {}).get("hits", []):
                metadata = item.get("metadata", {})
                title = metadata.get("title") or "unknown"
                desc = metadata.get("description") or ""
                text = f"{title}. {desc}"
                snippet = evidence_window(text, alias) or text[:300]
                name = alias.upper() if alias.isalpha() and len(alias) <= 12 else alias
                expansion = find_acronym_expansion(text, name)
                artifact_type = "software" if metadata.get("upload_type") == "software" else "unknown"
                results.append(Candidate(
                    id=stable_id("zenodo", item.get("id"), alias),
                    name=name,
                    expanded_form=expansion,
                    tolkien_entity=meta.get("entity"),
                    match_kind="full_acronym" if expansion else "name_only",
                    artifact_type=artifact_type,
                    domain="research artifact",
                    source_type="research_artifact",
                    source_name="Zenodo",
                    title=title,
                    authors=[c.get("name", "") for c in metadata.get("creators", [])],
                    published_date=metadata.get("publication_date"),
                    url=item.get("links", {}).get("html") or "https://zenodo.org/",
                    doi=metadata.get("doi"),
                    evidence_snippet=snippet,
                    raw_source_id=f"zenodo:{item.get('id')}",
                ))
    return results
```

- [ ] **Step 10: Smoke-test that all collectors import cleanly**

```bash
python -c "
from lotr_index.collectors import arxiv, github, huggingface, openalex, crossref, semantic_scholar, pypi, npm, zenodo
print('all collectors import OK')
"
```

Expected output: `all collectors import OK`

- [ ] **Step 11: Commit collectors**

```bash
git add src/lotr_index/collectors/
git commit -m "feat: add all source collectors"
```

---

### Task 6: CLI

**Files:**
- Create: `src/lotr_index/cli.py`

**Interfaces:**
- Consumes: all modules above
- Produces: `lotr-index sweep`, `lotr-index render`, `lotr-index validate`, `lotr-index promote --id`, `lotr-index reject --id`

- [ ] **Step 1: Verify CLI entry point is not yet callable**

```bash
lotr-index --help
```

Expected: error (cli.py doesn't exist / main() not defined).

- [ ] **Step 2: Write `src/lotr_index/cli.py`**

```python
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
```

- [ ] **Step 3: Re-install to register entry point**

```bash
pip install -e .[dev]
```

- [ ] **Step 4: Verify CLI is callable**

```bash
lotr-index --help
```

Expected output: shows `sweep`, `render`, `validate`, `promote`, `reject` subcommands.

- [ ] **Step 5: Run validate on empty data files**

```bash
lotr-index validate
```

Expected output:
```
OK: data/catalog.jsonl: 0 rows
OK: data/candidates.jsonl: 0 rows
OK: data/rejects.jsonl: 0 rows
```

- [ ] **Step 6: Run all tests to confirm nothing broke**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit CLI**

```bash
git add src/lotr_index/cli.py
git commit -m "feat: add CLI with sweep, render, validate, promote, reject"
```

---

### Task 7: GitHub Actions Workflow + README

**Files:**
- Create: `.github/workflows/daily-sweep.yml`
- Create: `README.md`

**Interfaces:**
- Produces: daily cron workflow at `17 3 * * *`; README with usage docs

- [ ] **Step 1: Write `.github/workflows/daily-sweep.yml`**

```yaml
name: Daily LOTR index sweep

on:
  workflow_dispatch:
  schedule:
    - cron: "17 3 * * *"

permissions:
  contents: write
  pull-requests: write

jobs:
  sweep:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install package
        run: |
          python -m pip install -U pip
          pip install -e .[dev]

      - name: Run daily sweep
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENALEX_API_KEY: ${{ secrets.OPENALEX_API_KEY }}
          SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_API_KEY }}
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          ZENODO_TOKEN: ${{ secrets.ZENODO_TOKEN }}
          CONTACT_EMAIL: ${{ vars.CONTACT_EMAIL }}
        run: |
          lotr-index sweep --days-back 3
          lotr-index validate
          lotr-index render

      - name: Commit updates
        run: |
          git config user.name "lotr-index-bot"
          git config user.email "actions@github.com"
          git add data docs README.md
          git diff --cached --quiet || git commit -m "Update LOTR index"
          git push
```

- [ ] **Step 2: Write `README.md`**

```markdown
# One Ring Index

Daily-updated index of Tolkien / Lord-of-the-Rings-inspired names, acronyms, backronyms, benchmarks, datasets, machine-learning models, packages, repositories, and software tools.

## Outputs

- Human-readable catalog: [`docs/index.md`](docs/index.md)
- Review queue: [`docs/candidates.md`](docs/candidates.md)
- JSON export: [`docs/catalog.json`](docs/catalog.json)
- CSV export: [`docs/catalog.csv`](docs/catalog.csv)

## What counts?

The index includes:

- Complete acronyms, such as a model named `GANDALF` with an expansion.
- Partial acronyms and backronyms.
- Name-only tools and projects, such as software named after Frodo, Gandalf, Legolas, or other Tolkien entities.
- Benchmarks, datasets, models, libraries, repositories, packages, and research artifacts.

## What does not count?

The index rejects entries where the Tolkien-like term is clearly unrelated. Examples: ring buffers, ELF binaries, Apache ORC files, and generic ring-road references.

## How it works

A daily GitHub Actions workflow queries metadata sources, extracts candidates, scores them, deduplicates them, and renders public outputs.

The system is API-first. It does not perform uncontrolled web crawling and does not mirror PDFs, package tarballs, or repository source code.

## Local usage

```bash
python -m pip install -U pip
pip install -e .[dev]
lotr-index sweep --days-back 3
lotr-index render
lotr-index validate
```

Run one source only:

```bash
lotr-index sweep --source arxiv --days-back 3
```

Promote a candidate:

```bash
lotr-index promote --id <candidate-id>
```

Reject a candidate:

```bash
lotr-index reject --id <candidate-id>
```

## Configuration

Edit:

- `config/tolkien_terms.yml` to add or modify Tolkien terms.
- `config/source_queries.yml` to modify context terms.
- `config/negative_terms.yml` to suppress known false positives.

## Review policy

Entries with high confidence are added to `data/catalog.jsonl`. Borderline entries go to `data/candidates.jsonl`. False positives go to `data/rejects.jsonl` so they are not repeatedly rediscovered.
```

- [ ] **Step 3: Commit workflow and README**

```bash
git add .github/workflows/daily-sweep.yml README.md
git commit -m "feat: add GitHub Actions workflow and README"
```

---

### Task 8: Integration Validation

This task runs the system end-to-end and verifies acceptance criteria from spec section 16.1.

**Files:** none created

- [ ] **Step 1: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS with no errors.

- [ ] **Step 2: Run arXiv sweep (single source)**

```bash
CONTACT_EMAIL=you@example.com lotr-index sweep --source arxiv --days-back 3
```

Expected:
- Command finishes without crashing
- Prints "Collecting from arxiv" and a candidate count
- `data/catalog.jsonl` and/or `data/candidates.jsonl` may contain entries
- `docs/index.md`, `docs/candidates.md`, `docs/catalog.csv`, `docs/catalog.json` all exist

- [ ] **Step 3: Validate output files**

```bash
lotr-index validate
```

Expected: all three `.jsonl` files pass with valid row counts.

- [ ] **Step 4: Verify docs exist**

```bash
ls docs/index.md docs/candidates.md docs/catalog.csv docs/catalog.json
```

Expected: all four files listed.

- [ ] **Step 5: Run render explicitly**

```bash
lotr-index render
```

Expected: no crash; docs regenerated.

- [ ] **Step 6: Run full sweep (optional collectors skip cleanly)**

```bash
CONTACT_EMAIL=you@example.com lotr-index sweep --days-back 3
```

Expected:
- Each collector prints its candidate count (zero is fine for skipped ones)
- No crash even if API keys are absent
- Final counts printed for catalog, review, rejects

- [ ] **Step 7: Final commit**

```bash
git add data docs
git commit -m "chore: initial sweep output and validated data files"
git push -u origin main
```

---

## Self-Review Against Spec

### Spec Coverage

| Spec section | Task |
|---|---|
| §4 Repository layout | Tasks 1, 7 |
| §5 Setup files (pyproject, .gitignore, .env.example, LICENSE, devcontainer) | Task 1 |
| §6 Config YAMLs (tolkien_terms, source_queries, negative_terms) | Task 1 |
| §7 Data model (Candidate schema, match_kind, artifact_type, status) | Task 2 |
| §8.1–8.3 __init__, model, storage | Task 2 |
| §8.4 http | Task 2 |
| §8.5 normalize | Task 2 |
| §8.6 score | Task 3 |
| §8.7 dedupe | Task 3 |
| §8.8 render | Task 4 |
| §8.9 logging_config | Task 2 |
| §9–10 All collectors (arxiv, github, hf, openalex, crossref, s2, pypi, npm, zenodo) | Task 5 |
| §11 CLI (sweep, render, validate, promote, reject) | Task 6 |
| §12 GitHub Actions workflow | Task 7 |
| §13 README | Task 7 |
| §14 Tests (normalize, score, dedupe, render) | Tasks 2–4 |
| §16.1 Local acceptance criteria | Task 8 |

### Placeholder Check

No TBDs, TODOs, or "similar to above" references — all code blocks are complete.

### Type Consistency

- `collect(terms: dict, days_back: int, max_results: int) -> list[Candidate]` — consistent across all 9 collectors
- `score_candidate(candidate: Candidate, term_weight: float) -> Candidate` — matches call in `cli.py`
- `dedupe(candidates: list[Candidate]) -> list[Candidate]` — matches call in `cli.py`
- `render_all()` — called from `cli.py` after each write operation
- `read_jsonl` / `write_jsonl` — types consistent throughout
