"""File-based LLM response cache to avoid redundant API calls."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_VERSION = "v1"


class LLMCache:
    def __init__(self, cache_dir: str | Path | None = None):
        if cache_dir is None:
            cache_dir = os.environ.get("LLM_CACHE_DIR", ".llm_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / ".index.json"
        self._index: dict[str, str] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self._index_file.exists():
            try:
                self._index = json.loads(self._index_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("[llm-cache] failed to load index: %s", exc)
                self._index = {}

    def _save_index(self) -> None:
        try:
            self._index_file.write_text(json.dumps(self._index, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("[llm-cache] failed to save index: %s", exc)

    def _make_key(self, prompt: str, model: str, extra: str = "") -> str:
        content = json.dumps(
            {"v": _CACHE_VERSION, "model": model, "extra": extra, "prompt": prompt},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, prompt: str, model: str, extra: str = "") -> Optional[str]:
        key = self._make_key(prompt, model, extra)
        if key not in self._index:
            return None
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            self._index.pop(key, None)
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data.get("response")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[llm-cache] failed to read cache %s: %s", key, exc)
            self._index.pop(key, None)
            return None

    def set(self, prompt: str, model: str, response: str, extra: str = "") -> None:
        key = self._make_key(prompt, model, extra)
        cache_file = self.cache_dir / f"{key}.json"
        try:
            cache_file.write_text(
                json.dumps(
                    {"model": model, "extra": extra, "prompt": prompt, "response": response},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._index[key] = f"{key}.json"
            self._save_index()
        except OSError as exc:
            logger.warning("[llm-cache] failed to write cache %s: %s", key, exc)

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except OSError:
                pass
        self._index = {}
        self._save_index()
        logger.info("[llm-cache] cleared")


_global_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache()
    return _global_cache
