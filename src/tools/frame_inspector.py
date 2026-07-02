"""
Tool: inspect_frame

Directs the VLM to perform deep analysis of a specific video frame.
New entities and relations discovered are back-propagated into the session's scene graph.

Real mode: calls VLClient → DashScope or vLLM (configured in configs/default.yaml).
Offline mode (cfg.mock.enabled / --mock): honest synthetic output, source="mock".
Real run with the backend unavailable (no API key / frame not on disk) fails loud
with an error rather than silently fabricating an observation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def _mock_inspect(timestamp: float) -> dict:
    """Honest synthetic inspection result for explicit offline mode.

    Makes no claim about the frame; the label and `mock_*` name keep it from
    ever passing as a real observation.
    """
    return {
        "answer": (
            f"[MOCK] Synthetic inspector output at t={timestamp:.1f}s — no vision "
            f"model was called. Enable a real backend for actual frame analysis."
        ),
        "entities_found": ["mock_subject", "mock_object"],
        "relations_found": [
            {"subject": "mock_subject", "relation": "mock_relation",
             "object": "mock_object"},
        ],
    }


def _fail_loud_inspect(frame_meta, cfg, reason: str) -> str:
    """Return an error observation instead of fabricating a frame reading."""
    return json.dumps({
        "error":                f"inspect_frame unavailable: {reason}",
        "answer":               f"inspect_frame unavailable: {reason}",
        "timestamp_used":       frame_meta.timestamp,
        "frame_id":             frame_meta.frame_id,
        "new_entities":         [],
        "new_triplets":         [],
        "nodes_added_to_graph": 0,
        "edges_added_to_graph": 0,
    })


def _extract_single_frame(session: "VideoSession", timestamp: float):
    """
    On-demand extraction of a single frame at `timestamp` seconds.
    Returns a FrameMeta if the video file is accessible, else None.
    """
    video_path = session.video_path
    if not Path(video_path).exists():
        return None
    try:
        import tempfile

        from PIL import Image
        from src.memory.session import FrameMeta

        try:
            import decord
            vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
            fps = vr.get_avg_fps()
            total = len(vr)
            idx = min(int(round(timestamp * fps)), total - 1)
            arr = vr[idx].asnumpy()
        except ImportError:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            idx = min(int(round(timestamp * fps)), total - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None
            arr = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        ts = round(float(idx) / fps, 2)
        frame_id = f"t_{ts:08.2f}"
        out_dir = Path(tempfile.gettempdir()) / "video_agent" / session.session_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{frame_id}.jpg"
        if not path.exists():
            Image.fromarray(arr).save(str(path), quality=85)

        meta = FrameMeta(frame_id=frame_id, timestamp=ts,
                         path=str(path), extracted=True)
        session.register_frames([meta])
        return meta
    except Exception:
        return None


def make_inspect_frame(session: "VideoSession"):
    """Factory that binds inspect_frame to the given VideoSession."""

    @tool
    def inspect_frame(timestamp: float, question: str) -> str:
        """
        Ask the VLM to examine the frame nearest to `timestamp` and answer
        a specific question. Newly discovered entities and relations are
        automatically merged back into the session's scene graph.

        Use this only when query_scene_graph cannot answer the question — for
        example to read text, count objects, identify faces, or resolve
        fine-grained spatial relationships.

        Args:
            timestamp: Target time in seconds (e.g. 34.5). The nearest cached
                       frame is selected automatically. If no frame is near
                       this timestamp, one is extracted on demand.
            question:  Focused question for the VLM, e.g.
                       "How many people are in the frame?" or
                       "What does the sign on the wall say?"

        Returns:
            JSON with keys:
            - answer         (str)        VLM's response
            - timestamp_used (float)      actual timestamp of the analyzed frame
            - frame_id       (str | null) frame identifier
            - new_entities   (list[str])  entity names added to scene graph
            - new_triplets   (list[dict]) triplets added to scene graph
        """
        from src.config import get_settings
        cfg = get_settings()

        # ── 1. find or extract the frame ──────────────────────────────────
        frame_meta = session.get_frame_by_timestamp(
            timestamp, tolerance=cfg.perception.frame_tolerance_sec
        )
        if frame_meta is None:
            frame_meta = _extract_single_frame(session, timestamp)

        if frame_meta is None:
            if session.cached_frames:
                frame_meta = next(iter(session.cached_frames.values()))
            else:
                return json.dumps({
                    "answer": (
                        "No frames are cached and no video file is accessible. "
                        "Call extract_keyframes first."
                    ),
                    "timestamp_used": timestamp,
                    "frame_id": None,
                    "new_entities": [],
                    "new_triplets": [],
                })

        # ── 2. produce inspection result (mock / fail-loud / real) ────────
        has_api_key = bool(
            cfg.dashscope_api_key if cfg.backend == "dashscope" else cfg.vllm_api_key
        )
        has_real_frame = bool(frame_meta.path and Path(frame_meta.path).exists())

        if cfg.mock.enabled:
            # Explicit offline mode: honest synthetic output, never on a real run.
            result = _mock_inspect(frame_meta.timestamp)
        elif not has_api_key:
            return _fail_loud_inspect(
                frame_meta, cfg,
                f"no API key for backend '{cfg.backend}' — set the key or enable "
                f"offline mode (mock.enabled: true / --mock)")
        elif not has_real_frame:
            return _fail_loud_inspect(
                frame_meta, cfg,
                "the target frame is not saved to disk, so it cannot be analyzed — "
                "call extract_keyframes first, or check the video path")
        else:
            from src.perception.vl_client import get_vl_client
            client = get_vl_client()
            result = client.inspect(frame_meta.path, question)

        # ── 3. back-propagate to scene graph ──────────────────────────────
        edge_source = "mock" if cfg.mock.enabled else "inspector"
        new_nodes = [
            {"name": name, "type": "object", "attributes": {}}
            for name in result["entities_found"]
        ]
        new_edges = [
            {
                "subject":    r["subject"],
                "relation":   r["relation"],
                "object":     r["object"],
                "t_start":    frame_meta.timestamp,
                "t_end":      frame_meta.timestamp + cfg.scene_graph.merge_window_sec,
                "confidence": cfg.scene_graph.confidence_threshold,
                "source":     edge_source,
            }
            for r in result["relations_found"]
            if isinstance(r, dict) and all(k in r for k in ("subject", "relation", "object"))
        ]
        stats = session.update_scene_graph(new_nodes, new_edges)

        new_triplets_out = [
            {"subject": r["subject"], "relation": r["relation"], "object": r["object"]}
            for r in result["relations_found"]
            if isinstance(r, dict) and all(k in r for k in ("subject", "relation", "object"))
        ]

        return json.dumps({
            "answer":               result["answer"],
            "timestamp_used":       frame_meta.timestamp,
            "frame_id":             frame_meta.frame_id,
            "new_entities":         result["entities_found"],
            "new_triplets":         new_triplets_out,
            "nodes_added_to_graph": stats["nodes_added"],
            "edges_added_to_graph": stats["edges_added"],
            "graph_size_after":     (
                f"{len(session.scene_graph.entities)} entities, "
                f"{len(session.scene_graph)} triplets"
            ),
        })

    return inspect_frame
