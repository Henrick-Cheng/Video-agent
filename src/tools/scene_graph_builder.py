"""
Tool: build_scene_graph

Analyzes specified keyframes with the VLM and merges discovered triplets into
the session's scene graph.

Real mode: calls VLClient → DashScope or vLLM (configured in configs/default.yaml).
Offline mode (cfg.mock.enabled / --mock): honest synthetic output for pipeline
smoke tests — clearly-labeled `mock_*` entities, source="mock".
Real run with the backend unavailable (no API key / no frames on disk) fails
loud with an error rather than silently fabricating evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


# ── Fail-loud + mock helpers ──────────────────────────────────────────────────

def _fail_loud(reason: str) -> str:
    """Return an error observation instead of fabricating scene-graph evidence.

    The agent surfaces this to the user rather than answering from fake data.
    """
    return json.dumps({
        "error":        f"build_scene_graph unavailable: {reason}",
        "new_triplets": [],
        "nodes_added":  0,
        "edges_added":  0,
        "_mode":        "error",
    })


def _mock_build(session: "VideoSession", frame_id_list: list[str], cfg) -> str:
    """Honest synthetic output for explicit offline mode (cfg.mock.enabled).

    Entities/relations use unmistakably synthetic names and source="mock" so
    they can never be confused with, or pass as, real VLM evidence. This only
    exercises the pipeline plumbing; it makes no claim about the video.
    """
    mock_nodes = [
        {"name": "mock_subject", "type": "person", "attributes": {"note": "synthetic"}},
        {"name": "mock_object",  "type": "object", "attributes": {"note": "synthetic"}},
    ]
    mock_edges = []
    for fid in frame_id_list[:6]:
        frame = session.get_frame(fid)
        ts = frame.timestamp if frame else 0.0
        window = cfg.scene_graph.merge_window_sec
        mock_edges.append(
            {"subject": "mock_subject", "relation": "mock_relation",
             "object": "mock_object", "t_start": ts, "t_end": ts + window,
             "confidence": 0.0, "source": "mock"})
    stats = session.update_scene_graph(mock_nodes, mock_edges)
    triplets_out = [
        {"subject": e["subject"], "relation": e["relation"], "object": e["object"]}
        for e in mock_edges
    ]
    return json.dumps({
        "new_triplets":  triplets_out,
        "nodes_added":   stats["nodes_added"],
        "edges_added":   stats["edges_added"],
        "graph_summary": session.scene_graph.to_text(),
        "_mode":         "mock",
    })


# ── Tool factory ──────────────────────────────────────────────────────────────

def make_build_scene_graph(session: "VideoSession"):
    """Factory that binds build_scene_graph to the given VideoSession."""

    @tool
    def build_scene_graph(frame_ids: str, focus_entities: str = "") -> str:
        """
        Analyze specified frames with the VLM and add discovered entities and
        relations to the session's scene graph.

        You do NOT need to process all frames — focus on frames most relevant
        to the current question.

        Args:
            frame_ids:      Comma-separated frame_id strings from a prior
                            extract_keyframes call, e.g.
                            "t_00000.00,t_00004.67,t_00009.33".
                            Pass "*" to process all cached frames.
            focus_entities: Optional comma-separated entity names to guide
                            the VLM, e.g. "person,bicycle,door".
                            Leave empty for general-purpose extraction.

        Returns:
            JSON with keys:
            - new_triplets  (list[dict])  triplets added in this call
            - nodes_added   (int)
            - edges_added   (int)
            - graph_summary (str)         scene graph as text
            - _mode         (str)         "real" | "mock" | "error"
        """
        from src.config import get_settings
        cfg = get_settings()

        if frame_ids.strip() == "*":
            frame_id_list = list(session.cached_frames.keys())
        else:
            frame_id_list = [fid.strip() for fid in frame_ids.split(",") if fid.strip()]

        focus_list = [e.strip() for e in focus_entities.split(",") if e.strip()]

        # Determine real vs mock path
        real_frame_ids = [
            fid for fid in frame_id_list
            if (f := session.get_frame(fid)) and f.path and Path(f.path).exists()
        ]

        has_api_key = bool(
            cfg.dashscope_api_key if cfg.backend == "dashscope" else cfg.vllm_api_key
        )

        # Explicit offline mode: honest synthetic output (never on a real run).
        if cfg.mock.enabled:
            return _mock_build(session, frame_id_list, cfg)

        # Real run: fail loud rather than silently fabricate evidence when the
        # backend is unavailable. A fabricated scene graph tagged source="vlm"
        # would be indistinguishable from real output and could contaminate
        # answers / benchmarks.
        if not has_api_key:
            return _fail_loud(
                f"no API key for backend '{cfg.backend}' — set the key in "
                f"configs/default.yaml or the env, or enable offline mode "
                f"(mock.enabled: true / --mock)")
        if not real_frame_ids:
            return _fail_loud(
                "none of the given frame_ids resolve to a frame file on disk — "
                "call extract_keyframes first, or check the video path")

        # ── Real VLM path ──────────────────────────────────────────────────
        from src.perception.vl_client import get_vl_client
        from src.scene_graph.builder import build_frames

        vl_client = get_vl_client()
        stats = build_frames(
            session=session,
            frame_ids=real_frame_ids,
            focus_entities=focus_list,
            vl_client=vl_client,
            merge_window_sec=cfg.scene_graph.merge_window_sec,
            confidence_threshold=cfg.scene_graph.confidence_threshold,
            batch_size=cfg.perception.batch_size,
            max_parallel_batches=cfg.perception.max_parallel_batches,
            cross_dedup_threshold=cfg.scene_graph.dedup_threshold,
        )
        return json.dumps({
            "new_triplets":  stats["new_relations"],
            "nodes_added":   stats["nodes_added"],
            "edges_added":   stats["edges_added"],
            "graph_summary": session.scene_graph.to_text(),
            "_mode":         "real",
            "_batches":      f"{stats['batches_ok']} ok / {stats['batches_fail']} failed",
        })

    return build_scene_graph
