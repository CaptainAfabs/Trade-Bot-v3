"""Simple TTL disk cache for adapter responses. JSON-on-disk under data/cache/<ns>.

Trade-off: not great for huge blobs, fine for one-shot per-ticker fetches.
Hot path during a request is one stat() + one read — negligible.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

CACHE_ROOT = Path("data/cache")


class DiskCache:
    def __init__(self, namespace: str) -> None:
        self.dir = CACHE_ROOT / namespace
        self.dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, ttl_seconds: int) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self._path(key).write_text(json.dumps(value, default=str), encoding="utf-8")
        except Exception:
            pass

    def _path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self.dir / f"{safe}.json"
