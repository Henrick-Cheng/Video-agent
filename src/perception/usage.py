"""
Global token-usage ledger.

Every OpenAI-compatible API response carries a real ``usage`` object
(prompt_tokens / completion_tokens, with image tokens already included in
prompt_tokens for VL models). VLClient records each response here, so any
caller can measure the true token cost of a code region:

    marker = LEDGER.marker()
    ... do work that triggers VL calls (possibly from worker threads) ...
    delta = LEDGER.since(marker)   # {"prompt_tokens", "completion_tokens", "calls"}

This replaces the old per-method estimates (chars/3, frames*1500) in the
benchmark, which mixed measurement methodologies across methods and carried a
language bias (see docs/progress.md, Phase 12 finding #3).

Thread-safe: scene-graph building issues VL calls from a ThreadPoolExecutor.
"""

from __future__ import annotations

import threading
from typing import Any, NamedTuple


class UsageRecord(NamedTuple):
    model: str
    prompt_tokens: int
    completion_tokens: int
    images: int = 0


class UsageLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[UsageRecord] = []

    def record(self, model: str, usage: Any, images: int = 0) -> None:
        """Append one API response's usage. Accepts the OpenAI SDK usage object
        (or any object with prompt_tokens/completion_tokens); None is a no-op.
        `images` counts the frames sent in the request (frames-touched metric)."""
        if usage is None:
            return
        rec = UsageRecord(
            model=model,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            images=images,
        )
        with self._lock:
            self._records.append(rec)

    def marker(self) -> int:
        """Position marker for later delta queries via since()."""
        with self._lock:
            return len(self._records)

    def since(self, marker: int) -> dict:
        """Aggregate usage recorded after *marker*."""
        with self._lock:
            recs = self._records[marker:]
        return {
            "prompt_tokens": sum(r.prompt_tokens for r in recs),
            "completion_tokens": sum(r.completion_tokens for r in recs),
            "calls": len(recs),
            "images": sum(r.images for r in recs),
        }


LEDGER = UsageLedger()
