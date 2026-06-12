"""
Tool: explore_segment (v2 lazy memory workhorse)

The agent decides WHERE in time to look and WHAT to look for; this tool
watches that window closely (≤6 frames, one multi-image VL call) and writes
both a dense caption (L1 evidence) and triplets (L2 index) into memory.

This replaces the v1 pattern of building the whole graph upfront: graph
construction itself becomes a per-question agent decision.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession

_MAX_FRAMES = 6


def _extract_window_frames(session: "VideoSession", t_start: float,
                           t_end: float, count: int) -> list:
    """Extract `count` uniform frames within [t_start, t_end] and register them."""
    from src.tools.keyframe import _open_video, _save_frames, _frame_dir
    from src.config import get_settings

    backend, reader, fps, total = _open_video(session.video_path)
    duration = total / fps if fps else 0.0
    t0 = max(0.0, min(t_start, duration))
    t1 = max(t0, min(t_end, duration))

    if t1 - t0 < 0.5:  # degenerate window → single frame
        ts_list = [t0]
    else:
        step = (t1 - t0) / (count - 1) if count > 1 else 0
        ts_list = [t0 + i * step for i in range(count)]

    indices = [min(int(t * fps), max(total - 1, 0)) for t in ts_list]
    quality = get_settings().perception.image_quality
    metas = _save_frames(backend, reader, indices, fps, _frame_dir(session), quality)
    session.register_frames(metas)
    return sorted(metas, key=lambda m: m.timestamp)


def make_explore_segment(session: "VideoSession"):
    """Factory binding explore_segment to the given VideoSession."""

    @tool
    def explore_segment(t_start: float, t_end: float, focus: str = "") -> str:
        """
        Watch a time window of the video closely and add what is seen to memory.

        Use this when current memory cannot answer the question: pick the most
        promising window (guided by the transcript timestamps, the global
        summary, or earlier hits) and state what to look for in `focus`.

        Args:
            t_start: Window start in seconds.
            t_end:   Window end in seconds (a 10-30s window works well).
            focus:   What to look for, e.g. "which word is printed on the bottle".

        Returns:
            JSON: {segment_id, t_start, t_end, caption, nodes_added,
                   edges_added, explored_windows}
        """
        from src.perception.vl_client import get_vl_client
        from src.scene_graph.builder import build_segment

        try:
            frames = _extract_window_frames(session, t_start, t_end, _MAX_FRAMES)
        except Exception as exc:
            return json.dumps({"error": f"frame extraction failed: {exc}"})
        if not frames:
            return json.dumps({"error": "no frames could be extracted in this window"})

        result = build_segment(session, frames, get_vl_client(), question=focus)
        if not result.get("ok"):
            return json.dumps({"error": "VLM analysis of the window failed"})

        return json.dumps({
            "segment_id": result["segment_id"],
            "t_start": result["t_start"],
            "t_end": result["t_end"],
            "caption": result["caption"],
            "nodes_added": result["nodes_added"],
            "edges_added": result["edges_added"],
            "explored_windows": session.explored_windows(),
        }, ensure_ascii=False)

    return explore_segment
