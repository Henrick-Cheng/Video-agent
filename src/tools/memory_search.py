"""
Tool: search_memory (v2)

Cheap unified lookup over all three lazy-memory layers: triplet index (L2),
explored-segment captions (L1), and the narration transcript (L0). Zero API
cost — always try this before exploring.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def make_search_memory(session: "VideoSession"):
    """Factory binding search_memory to the given VideoSession."""

    @tool
    def search_memory(question: str) -> str:
        """
        Search everything known about the video so far: structured facts
        (with timestamps), notes from previously explored windows, and the
        narration transcript. Fast and free — always try this BEFORE
        explore_segment.

        Args:
            question: Natural-language query, e.g. "when does he open the box".

        Returns:
            JSON: {triplets, segments, transcript_hits, entity_summary,
                   explored_windows, found}
        """
        from src.scene_graph.retriever import search_memory as _search

        return json.dumps(_search(question, session), ensure_ascii=False)

    return search_memory
