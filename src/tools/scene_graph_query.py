"""
Tool: query_scene_graph

Retrieves relevant triplets from the session's scene graph using a
multi-strategy Chinese retriever (jieba + exact/relation/substring matching).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def make_query_scene_graph(session: "VideoSession"):
    """Factory that binds query_scene_graph to the given VideoSession."""

    @tool
    def query_scene_graph(question: str) -> str:
        """
        Search the session's scene graph for triplets relevant to the question.

        Always try this BEFORE calling inspect_frame. The scene graph is fast
        and structured; inspect_frame is expensive. If the result says the graph
        is empty, call build_scene_graph first.

        Args:
            question: Natural-language question used to guide retrieval,
                      e.g. "自行车旁边的人在做什么？"

        Returns:
            JSON with keys:
            - triplets        (list[dict])  matched triplets, sorted by score
            - entity_summary  (str)         all known entities
            - found           (bool)        True if any triplets matched
            - matched_tokens  (list[str])   query tokens that produced hits
            - nearby_entities (list[str])   close-match entities when found=False
        """
        from src.config import get_settings
        from src.scene_graph.retriever import retrieve_triplets

        cfg = get_settings()

        if len(session.scene_graph) == 0:
            return json.dumps({
                "triplets": [],
                "entity_summary": "Scene graph is empty. Call build_scene_graph first.",
                "found": False,
                "matched_tokens": [],
                "nearby_entities": [],
            }, ensure_ascii=False)

        result = retrieve_triplets(
            question=question,
            graph=session.scene_graph,
            top_k=cfg.retrieval.top_k,
            min_score=cfg.retrieval.min_score,
        )
        return json.dumps(result, ensure_ascii=False)

    return query_scene_graph
