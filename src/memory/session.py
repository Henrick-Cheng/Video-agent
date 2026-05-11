"""
VideoSession: shared mutable state for a single video Q&A session.

All Agent tools receive a reference to the same session instance and
read/write it directly — no message passing needed between tools.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from src.scene_graph.graph import SceneGraph, Triplet


@dataclass
class FrameMeta:
    frame_id: str
    timestamp: float           # seconds into the video
    path: Optional[str] = None # absolute path to saved JPEG, None if not yet written
    extracted: bool = False


class VideoSession:
    """
    Shared state container for one video question-answering turn.

    Attributes
    ----------
    video_path    : Path to the source video file.
    session_id    : Auto-generated unique identifier.
    scene_graph   : Temporal scene graph — the Agent's working memory.
    cached_frames : Registered keyframes, keyed by frame_id.
    query_history : Natural-language questions asked so far in this session.
    """

    def __init__(self, video_path: str, session_id: Optional[str] = None) -> None:
        self.video_path: str = video_path
        self.session_id: str = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        self.scene_graph: SceneGraph = SceneGraph()
        self.cached_frames: dict[str, FrameMeta] = {}
        self.query_history: list[str] = []

    # ── frame registry ────────────────────────────────────────────────────────

    def register_frames(self, frames: list[FrameMeta]) -> None:
        for f in frames:
            self.cached_frames[f.frame_id] = f

    def get_frame(self, frame_id: str) -> Optional[FrameMeta]:
        return self.cached_frames.get(frame_id)

    def get_frame_by_timestamp(
        self, timestamp: float, tolerance: Optional[float] = None
    ) -> Optional[FrameMeta]:
        """Return the registered frame closest to `timestamp` within `tolerance` seconds."""
        if tolerance is None:
            try:
                from src.config import get_settings
                tolerance = get_settings().scene_graph.timestamp_tolerance
            except Exception:
                tolerance = 0.5

        if not self.cached_frames:
            return None
        closest = min(self.cached_frames.values(),
                      key=lambda f: abs(f.timestamp - timestamp))
        if abs(closest.timestamp - timestamp) <= tolerance:
            return closest
        return None

    # ── scene graph ───────────────────────────────────────────────────────────

    def update_scene_graph(
        self,
        new_nodes: list[dict],
        new_edges: list[dict],
    ) -> dict[str, int]:
        """
        Progressively merge nodes and edges into the scene graph with deduplication.

        Parameters
        ----------
        new_nodes : list of dicts with keys: "name" (required), "type", "attributes",
                    "first_seen", "last_seen" (optional)
        new_edges : list of dicts with keys:
                    "subject", "relation", "object" (required)
                    "t_start", "t_end", "confidence", "source" (optional)
        """
        nodes_added = 0
        for node in new_nodes:
            added = self.scene_graph.add_entity(
                node["name"],
                node.get("type", "object"),
                node.get("attributes"),
                node.get("first_seen", 0.0),
                node.get("last_seen", 0.0),
            )
            if added:
                nodes_added += 1

        edges_added = 0
        for edge in new_edges:
            triplet = Triplet(
                subject=edge["subject"],
                relation=edge["relation"],
                object=edge["object"],
                t_start=edge.get("t_start", 0.0),
                t_end=edge.get("t_end", 0.0),
                confidence=edge.get("confidence", 1.0),
                source=edge.get("source", "vlm"),
            )
            if self.scene_graph.add_triplet(triplet):
                edges_added += 1

        return {"nodes_added": nodes_added, "edges_added": edges_added}

    def get_subgraph(self, entities: list[str]) -> dict:
        """Extract a subgraph dict for the given entity names."""
        relevant_triplets = self.scene_graph.get_triplets_for_entities(entities)
        touched: set[str] = set()
        for t in relevant_triplets:
            touched.add(t.subject)
            touched.add(t.object)

        sg = self.scene_graph
        return {
            "entities": {
                name: {
                    "type":       sg.entities[name].entity_type,
                    "attributes": sg.entities[name].attributes,
                }
                for name in touched
                if name in sg.entities
            },
            "triplets": [
                {
                    "subject":    t.subject,
                    "relation":   t.relation,
                    "object":     t.object,
                    "t_start":    t.t_start,
                    "t_end":      t.t_end,
                    "confidence": t.confidence,
                }
                for t in relevant_triplets
            ],
        }

    # ── misc ──────────────────────────────────────────────────────────────────

    def add_query(self, question: str) -> None:
        self.query_history.append(question)

    def summary(self) -> str:
        return (
            f"Session {self.session_id} | video={self.video_path} | "
            f"frames={len(self.cached_frames)} | "
            f"graph: {len(self.scene_graph.entities)} entities, "
            f"{len(self.scene_graph)} triplets"
        )

    def __repr__(self) -> str:
        return f"VideoSession(id={self.session_id!r}, video={self.video_path!r})"
