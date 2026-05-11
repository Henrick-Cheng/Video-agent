"""
Tool: inspect_frame

Directs the VLM to perform deep analysis of a specific video frame.
New entities and relations discovered are back-propagated into the session's scene graph.

Real mode: calls VLClient → DashScope or vLLM (configured in configs/default.yaml).
Mock fallback: used when frame has no saved path (video not on disk).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


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
                       "图中有多少人？" or "墙上的牌子写的什么？"

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

        # ── 2. call VLM (real or mock) ────────────────────────────────────
        if frame_meta.path and Path(frame_meta.path).exists():
            from src.perception.vl_client import get_vl_client
            client = get_vl_client()
            result = client.inspect(frame_meta.path, question)
        else:
            result = {
                "answer": (
                    f"[MOCK] At t={frame_meta.timestamp:.1f}s: A person in a red jacket "
                    f"is riding a blue bicycle through an intersection. "
                    f"The traffic light is green."
                ),
                "entities_found": ["person_A", "bicycle", "traffic_light"],
                "relations_found": [
                    {"subject": "person_A", "relation": "骑乘",   "object": "bicycle"},
                    {"subject": "bicycle",  "relation": "穿过", "object": "intersection"},
                ],
            }

        # ── 3. back-propagate to scene graph ──────────────────────────────
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
                "source":     "inspector",
            }
            for r in result["relations_found"]
            if isinstance(r, dict) and all(k in r for k in ("subject", "relation", "object"))
        ]
        session.update_scene_graph(new_nodes, new_edges)

        new_triplets_out = [
            {"subject": r["subject"], "relation": r["relation"], "object": r["object"]}
            for r in result["relations_found"]
            if isinstance(r, dict) and all(k in r for k in ("subject", "relation", "object"))
        ]

        return json.dumps({
            "answer":         result["answer"],
            "timestamp_used": frame_meta.timestamp,
            "frame_id":       frame_meta.frame_id,
            "new_entities":   result["entities_found"],
            "new_triplets":   new_triplets_out,
        })

    return inspect_frame
