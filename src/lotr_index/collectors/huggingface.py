from __future__ import annotations

import logging
import os

from huggingface_hub import HfApi

from ..model import Candidate
from ..normalize import evidence_window, stable_id

log = logging.getLogger(__name__)


def collect(terms: dict, days_back: int = 3, max_results: int = 50) -> list[Candidate]:
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
