"""
Tool: inspect_frame

Directs the VLM to perform deep analysis of a specific video frame.
New entities discovered here are back-propagated into the session's scene graph.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def make_inspect_frame(session: "VideoSession"):
    """Factory that binds inspect_frame to the given VideoSession."""

    @tool
    def inspect_frame(timestamp: float, question: str) -> str:
        """
        Ask the VLM to carefully examine the frame nearest to `timestamp`
        and answer a specific question. Any new entities or relations the VLM
        discovers are automatically merged back into the session's scene graph.

        Use this only when query_scene_graph cannot answer the question — for
        example to read text, count objects, identify faces, or resolve
        fine-grained spatial relationships.

        Args:
            timestamp: Target time in seconds (e.g. 34.5). The nearest cached
                       frame is selected automatically. If no frame is cached
                       near this timestamp, call extract_keyframes first.
            question:  Focused question for the VLM, e.g.
                       "How many fingers is the person holding up?" or
                       "What does the sign on the door say?"

        Returns:
            JSON with keys:
            - answer          (str)        VLM's response to the question
            - timestamp_used  (float)      actual timestamp of the analyzed frame
            - frame_id        (str | null) frame_id of the analyzed frame
            - new_entities    (list[str])  entity names added to scene graph
            - new_triplets    (list[dict]) triplets added to scene graph
        """
        # TODO: replace mock with real VLM inference
        #
        # frame_meta = session.get_frame_by_timestamp(timestamp, tolerance=2.0)
        # if frame_meta is None:
        #     return json.dumps({"answer": "No cached frame near this timestamp. "
        #                                  "Call extract_keyframes first.",
        #                        "timestamp_used": timestamp, "frame_id": None,
        #                        "new_entities": [], "new_triplets": []})
        #
        # from src.perception.vlm import VLMPerception
        # vlm = VLMPerception.get_instance(use_mock=False)
        # answer = vlm.answer_question(frame_meta.path, question)
        # new_triplets_raw = vlm.extract_triplets(frame_meta.path,
        #                                         timestamp=frame_meta.timestamp)
        # new_nodes = [{"name": t["subject"]}, {"name": t["object"]}
        #              for t in new_triplets_raw]
        # session.update_scene_graph(new_nodes, new_triplets_raw)

        # ── MOCK ──────────────────────────────────────────────────────────────
        frame_meta = session.get_frame_by_timestamp(timestamp, tolerance=5.0)

        if frame_meta is None:
            if session.cached_frames:
                # fallback to any available frame
                frame_meta = next(iter(session.cached_frames.values()))
            else:
                return json.dumps({
                    "answer": (
                        "No frames are cached. Call extract_keyframes first."
                    ),
                    "timestamp_used": timestamp,
                    "frame_id": None,
                    "new_entities": [],
                    "new_triplets": [],
                })

        mock_answer = (
            f"At t={frame_meta.timestamp:.1f}s: A person wearing a red jacket "
            f"is riding a blue bicycle through an intersection. The traffic light "
            f"is green. A pedestrian in a dark coat is standing on the sidewalk "
            f"to the right."
        )

        # back-propagate newly discovered entities into the scene graph
        new_nodes = [
            {"name": "pedestrian",   "type": "person",  "attributes": {"clothing": "dark coat"}},
            {"name": "sidewalk",     "type": "scene",   "attributes": {}},
            {"name": "intersection", "type": "scene",   "attributes": {}},
        ]
        new_edges = [
            {
                "subject": "pedestrian", "relation": "standing_on",
                "object":  "sidewalk",
                "t_start": frame_meta.timestamp, "t_end": frame_meta.timestamp + 2.0,
                "confidence": 0.79, "source": "inspector",
            },
            {
                "subject": "bicycle",  "relation": "crossing",
                "object":  "intersection",
                "t_start": frame_meta.timestamp, "t_end": frame_meta.timestamp + 4.0,
                "confidence": 0.86, "source": "inspector",
            },
        ]
        session.update_scene_graph(new_nodes, new_edges)

        new_entity_names = [n["name"] for n in new_nodes]
        new_triplets_out = [
            {"subject": e["subject"], "relation": e["relation"], "object": e["object"]}
            for e in new_edges
        ]

        return json.dumps({
            "answer":         mock_answer,
            "timestamp_used": frame_meta.timestamp,
            "frame_id":       frame_meta.frame_id,
            "new_entities":   new_entity_names,
            "new_triplets":   new_triplets_out,
        })

    return inspect_frame
