"""
Tool: query_scene_graph

Retrieves relevant triplets from the session's scene graph.
This is a cheap structured lookup — prefer it over inspect_frame.
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
                      e.g. "What is the person near the bicycle doing?"

        Returns:
            JSON with keys:
            - triplets       (list[dict])  matched triplets (up to 10)
            - entity_summary (str)         all known entities
            - found          (bool)        False if graph is empty
        """
        # TODO: replace naive keyword match with FAISS vector retrieval
        #
        # from sentence_transformers import SentenceTransformer
        # encoder = SentenceTransformer("all-MiniLM-L6-v2")
        # q_emb = encoder.encode(question)
        #
        # entity_embs = encoder.encode(list(session.scene_graph.entities.keys()))
        # scores = cosine_similarity([q_emb], entity_embs)[0]
        # top_entities = [name for name, _ in
        #                 sorted(zip(session.scene_graph.entities, scores),
        #                        key=lambda x: x[1], reverse=True)[:5]]
        # triplets = session.scene_graph.get_triplets_for_entities(top_entities)

        # ── MOCK ──────────────────────────────────────────────────────────────
        if len(session.scene_graph) == 0:
            return json.dumps({
                "triplets": [],
                "entity_summary": "Scene graph is empty. Call build_scene_graph first.",
                "found": False,
            })

        words = set(question.lower().split())
        matched_entities = [
            name for name in session.scene_graph.entities
            if any(kw in name.lower() for kw in words)
        ]
        # fallback: return first few entities if no keyword match
        if not matched_entities:
            matched_entities = list(session.scene_graph.entities.keys())[:4]

        relevant = session.scene_graph.get_triplets_for_entities(matched_entities)

        triplets_out = [
            {
                "subject":    t.subject,
                "relation":   t.relation,
                "object":     t.object,
                "t_start":    t.t_start,
                "t_end":      t.t_end,
                "confidence": t.confidence,
            }
            for t in relevant[:10]
        ]

        entity_names = list(session.scene_graph.entities.keys())
        entity_summary = f"Entities in graph ({len(entity_names)}): {', '.join(entity_names)}"

        return json.dumps({
            "triplets":       triplets_out,
            "entity_summary": entity_summary,
            "found":          bool(triplets_out),
        })

    return query_scene_graph
