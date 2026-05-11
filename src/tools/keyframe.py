"""
Tool: extract_keyframes

Extracts keyframes from a video on demand and registers them in VideoSession.
The Agent calls this first to get visual access to the video.
"""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


def make_extract_keyframes(session: "VideoSession"):
    """Factory that binds extract_keyframes to the given VideoSession."""

    @tool
    def extract_keyframes(strategy: str, count: int) -> str:
        """
        Extract keyframes from the video and register them in the session.

        Call this first when you need visual information. Choose strategy
        based on the question type:
        - "uniform"      → evenly spaced frames, good for broad questions
        - "scene_change" → frames at shot boundaries, good for event detection
        - "query_aware"  → frames near semantically relevant moments (requires
                           an existing scene graph; falls back to uniform if empty)

        Args:
            strategy: One of "uniform", "scene_change", "query_aware".
            count:    Number of frames to extract. Use 8 for quick overview,
                      16–32 for dense analysis.

        Returns:
            JSON with keys:
            - frame_ids    (list[str])  registered frame identifiers
            - timestamps   (list[float]) corresponding timestamps in seconds
            - total_cached (int)        total frames now in session cache
        """
        # TODO: replace with real decord-based extraction
        #
        # import decord
        # vr = decord.VideoReader(session.video_path, ctx=decord.cpu(0))
        # fps = vr.get_avg_fps()
        # total_frames = len(vr)
        # duration = total_frames / fps
        #
        # if strategy == "uniform":
        #     indices = np.linspace(0, total_frames - 1, count, dtype=int)
        # elif strategy == "scene_change":
        #     indices = _detect_scene_changes(vr, count)
        # elif strategy == "query_aware":
        #     indices = _query_aware_sampling(session, vr, count)
        #
        # frames = vr.get_batch(indices).asnumpy()
        # ... save as JPEG, create FrameMeta objects, session.register_frames(...)

        # ── MOCK ──────────────────────────────────────────────────────────────
        from src.memory.session import FrameMeta  # imported here to avoid circular

        mock_duration = 120.0  # seconds

        if strategy == "uniform":
            timestamps = [mock_duration * i / max(count - 1, 1) for i in range(count)]
        else:
            timestamps = sorted(random.uniform(0, mock_duration) for _ in range(count))

        frames = [
            FrameMeta(
                frame_id=f"frame_{int(ts * 10):06d}",
                timestamp=round(ts, 2),
                path=f"/tmp/video_agent_frames/frame_{int(ts * 10):06d}.jpg",
                extracted=True,
            )
            for ts in timestamps
        ]
        session.register_frames(frames)

        return json.dumps({
            "frame_ids": [f.frame_id for f in frames],
            "timestamps": [f.timestamp for f in frames],
            "total_cached": len(session.cached_frames),
        })

    return extract_keyframes
