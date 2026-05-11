"""
Tool: build_scene_graph

Calls the VLM on specified frames to extract triplets and merge them
into the session's scene graph. Build is always on-demand, never full-video.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def make_build_scene_graph(session: "VideoSession"):
    """Factory that binds build_scene_graph to the given VideoSession."""

    @tool
    def build_scene_graph(frame_ids: str, focus_entities: str = "") -> str:
        """
        Analyze the specified frames with the VLM and add discovered triplets
        to the session's scene graph. You do NOT need to process all frames —
        focus on the frames most relevant to the current question.

        Args:
            frame_ids:      Comma-separated frame_id strings from a prior
                            extract_keyframes call, e.g.
                            "frame_000000,frame_085714,frame_171428".
                            Pass "*" to process all cached frames.
            focus_entities: Optional comma-separated entity names to guide
                            the VLM's attention, e.g. "person,bicycle,door".
                            Leave empty for general-purpose extraction.

        Returns:
            JSON with keys:
            - new_triplets  (list[dict])  triplets added in this call
            - nodes_added   (int)
            - edges_added   (int)
            - graph_summary (str)         full scene graph as text
        """
        # TODO: replace mock with real VLM perception loop
        #
        # from src.perception.vlm import VLMPerception
        # vlm = VLMPerception.get_instance(use_mock=False)
        # focus_list = [e.strip() for e in focus_entities.split(",") if e.strip()]
        #
        # all_nodes, all_edges = [], []
        # for fid in frame_id_list:
        #     frame = session.get_frame(fid)
        #     if frame is None:
        #         continue
        #     triplets = vlm.extract_triplets(frame.path, focus_list, frame.timestamp)
        #     for t in triplets:
        #         all_nodes += [{"name": t["subject"]}, {"name": t["object"]}]
        #         all_edges.append(t)
        #
        # stats = session.update_scene_graph(all_nodes, all_edges)

        # ── MOCK ──────────────────────────────────────────────────────────────
        if frame_ids.strip() == "*":
            frame_id_list = list(session.cached_frames.keys())
        else:
            frame_id_list = [fid.strip() for fid in frame_ids.split(",") if fid.strip()]

        mock_nodes = [
            {"name": "person_A", "type": "person",
             "attributes": {"clothing": "red jacket", "gender": "unknown"}},
            {"name": "bicycle",  "type": "object",
             "attributes": {"color": "blue", "brand": "unknown"}},
            {"name": "traffic_light", "type": "object",
             "attributes": {"state": "green"}},
            {"name": "road",     "type": "scene", "attributes": {}},
        ]

        mock_edges = []
        for fid in frame_id_list[:6]:  # process up to 6 frames in mock
            frame = session.get_frame(fid)
            ts = frame.timestamp if frame else 0.0
            mock_edges += [
                {"subject": "person_A", "relation": "riding",
                 "object": "bicycle",      "t_start": ts, "t_end": ts + 3.0,
                 "confidence": 0.92, "source": "vlm"},
                {"subject": "bicycle",   "relation": "on",
                 "object": "road",        "t_start": ts, "t_end": ts + 3.0,
                 "confidence": 0.88, "source": "vlm"},
                {"subject": "person_A",  "relation": "approaching",
                 "object": "traffic_light", "t_start": ts, "t_end": ts + 8.0,
                 "confidence": 0.81, "source": "vlm"},
            ]

        stats = session.update_scene_graph(mock_nodes, mock_edges)

        new_triplets_out = [
            {
                "subject":  e["subject"],
                "relation": e["relation"],
                "object":   e["object"],
                "t_start":  e["t_start"],
                "t_end":    e["t_end"],
            }
            for e in mock_edges
        ]

        return json.dumps({
            "new_triplets":  new_triplets_out,
            "nodes_added":   stats["nodes_added"],
            "edges_added":   stats["edges_added"],
            "graph_summary": session.scene_graph.to_text(max_triplets=15),
        })

    return build_scene_graph
