"""
Tool: extract_keyframes

Extracts keyframes from a video on demand and registers them in VideoSession.
Real implementation uses decord (uniform/query_aware) and PySceneDetect (scene_change).
Falls back gracefully to mock when video path doesn't exist.
"""

from __future__ import annotations

import json
import tempfile
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from src.memory.session import VideoSession


# ── private helpers ───────────────────────────────────────────────────────────

def _frame_dir(session: "VideoSession") -> Path:
    """Consistent per-session frame cache directory under /tmp."""
    d = Path(tempfile.gettempdir()) / "video_agent" / session.session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_frames(indices: list[int], vr, fps: float, out_dir: Path) -> list:
    """Batch-decode and JPEG-save frames; return list of FrameMeta."""
    import numpy as np
    from PIL import Image
    from src.memory.session import FrameMeta

    unique = sorted(set(int(i) for i in indices))
    arrays = vr.get_batch(unique).asnumpy()
    metas = []
    for idx, arr in zip(unique, arrays):
        ts = round(float(idx) / fps, 2)
        frame_id = f"t_{ts:08.2f}"
        path = out_dir / f"{frame_id}.jpg"
        if not path.exists():
            Image.fromarray(arr).save(str(path), quality=85)
        metas.append(FrameMeta(frame_id=frame_id, timestamp=ts,
                               path=str(path), extracted=True))
    return metas


def _uniform_indices(total_frames: int, count: int) -> list[int]:
    import numpy as np
    return list(np.linspace(0, total_frames - 1, count, dtype=int))


def _detect_scene_changes(video_path: str, max_count: int,
                           total_frames: int) -> list[int]:
    """
    Use PySceneDetect to find shot boundaries.
    Falls back to uniform if PySceneDetect is not installed or detects no scenes.
    """
    try:
        from scenedetect import detect, AdaptiveDetector
        scene_list = detect(video_path, AdaptiveDetector())
        indices = [s[0].get_frames() for s in scene_list]
        if not indices:
            return _uniform_indices(total_frames, max_count)
        if len(indices) > max_count:
            step = max(1, len(indices) // max_count)
            indices = indices[::step][:max_count]
        return indices
    except ImportError:
        warnings.warn(
            "PySceneDetect not installed; falling back to uniform sampling. "
            "Install with: pip install scenedetect[opencv]"
        )
        return _uniform_indices(total_frames, max_count)


# ── tool factory ──────────────────────────────────────────────────────────────

def make_extract_keyframes(session: "VideoSession"):
    """Factory that binds extract_keyframes to the given VideoSession."""

    @tool
    def extract_keyframes(strategy: str, count: int) -> str:
        """
        Extract keyframes from the video and register them in the session.

        Call this first when you need visual information. Choose strategy
        based on the question type:
        - "uniform"      → evenly spaced frames, good for broad questions
        - "scene_change" → frames at shot boundaries (PySceneDetect), good for
                           event detection; falls back to uniform if not installed
        - "query_aware"  → currently falls back to uniform; CLIP-based retrieval
                           will be wired here in a future iteration

        Args:
            strategy: One of "uniform", "scene_change", "query_aware".
            count:    Number of frames to extract. Use 8 for quick overview,
                      16–32 for dense analysis.

        Returns:
            JSON with keys:
            - frame_ids    (list[str])   registered frame identifiers (format: t_XXXXXXXX.XX)
            - timestamps   (list[float]) corresponding timestamps in seconds
            - total_cached (int)         total frames now in session cache
        """
        video_path = session.video_path

        # ── real path ─────────────────────────────────────────────────────────
        if Path(video_path).exists():
            import decord
            import numpy as np

            vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
            fps = vr.get_avg_fps()
            total = len(vr)
            out_dir = _frame_dir(session)

            if strategy == "uniform" or strategy == "query_aware":
                # query_aware: TODO replace with CLIP-guided sampling
                indices = _uniform_indices(total, count)
            elif strategy == "scene_change":
                indices = _detect_scene_changes(video_path, count, total)
            else:
                raise ValueError(f"Unknown strategy: {strategy!r}")

            frame_metas = _save_frames(indices, vr, fps, out_dir)
            session.register_frames(frame_metas)

            return json.dumps({
                "frame_ids":    [f.frame_id for f in frame_metas],
                "timestamps":   [f.timestamp for f in frame_metas],
                "total_cached": len(session.cached_frames),
            })

        # ── mock fallback (no video file) ─────────────────────────────────────
        import random
        from src.memory.session import FrameMeta

        mock_duration = 120.0
        if strategy == "uniform" or strategy == "query_aware":
            timestamps = [round(mock_duration * i / max(count - 1, 1), 2)
                          for i in range(count)]
        else:
            timestamps = sorted(round(random.uniform(0, mock_duration), 2)
                                for _ in range(count))

        frames = [
            FrameMeta(
                frame_id=f"t_{ts:08.2f}",
                timestamp=ts,
                path=None,
                extracted=False,
            )
            for ts in timestamps
        ]
        session.register_frames(frames)

        return json.dumps({
            "frame_ids":    [f.frame_id for f in frames],
            "timestamps":   [f.timestamp for f in frames],
            "total_cached": len(session.cached_frames),
        })

    return extract_keyframes
