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
