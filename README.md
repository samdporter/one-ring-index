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
