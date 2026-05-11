"""
Tool: extract_keyframes

Extracts keyframes from a video on demand and registers them in VideoSession.
Video backend: tries decord first, falls back to OpenCV (cv2) if decord is
unavailable (e.g. Python 3.13 / macOS where no decord wheel exists).
Scene-change detection uses PySceneDetect when installed.
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
    d = Path(tempfile.gettempdir()) / "video_agent" / session.session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _open_video(video_path: str):
    """Return (backend, reader, fps, total_frames)."""
    try:
        import decord
        vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
        return ("decord", vr, vr.get_avg_fps(), len(vr))
    except ImportError:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return ("cv2", cap, fps, total)


def _save_frames(backend: str, reader, indices: list[int],
                 fps: float, out_dir: Path, image_quality: int) -> list:
    from PIL import Image
    from src.memory.session import FrameMeta

    unique = sorted(set(int(i) for i in indices))
    metas = []

    if backend == "decord":
        arrays = reader.get_batch(unique).asnumpy()
        for idx, arr in zip(unique, arrays):
            ts = round(float(idx) / fps, 2)
            frame_id = f"t_{ts:08.2f}"
            path = out_dir / f"{frame_id}.jpg"
            if not path.exists():
                Image.fromarray(arr).save(str(path), quality=image_quality)
            metas.append(FrameMeta(frame_id=frame_id, timestamp=ts,
                                   path=str(path), extracted=True))
    else:
        import cv2
        for idx in unique:
            reader.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = reader.read()
            if not ret:
                continue
            import numpy as np
            arr = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ts = round(float(idx) / fps, 2)
            frame_id = f"t_{ts:08.2f}"
            path = out_dir / f"{frame_id}.jpg"
            if not path.exists():
                Image.fromarray(arr).save(str(path), quality=image_quality)
            metas.append(FrameMeta(frame_id=frame_id, timestamp=ts,
                                   path=str(path), extracted=True))
        reader.release()

    return metas


def _uniform_indices(total_frames: int, count: int) -> list[int]:
    import numpy as np
    return list(np.linspace(0, total_frames - 1, count, dtype=int))


def _detect_scene_changes(video_path: str, max_count: int,
                           total_frames: int) -> list[int]:
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
            - frame_ids    (list[str])   registered frame identifiers
            - timestamps   (list[float]) corresponding timestamps in seconds
            - total_cached (int)         total frames now in session cache
        """
        from src.config import get_settings
        cfg = get_settings()

        video_path = session.video_path

        if Path(video_path).exists():
            backend, reader, fps, total = _open_video(video_path)
            out_dir = _frame_dir(session)

            if strategy in ("uniform", "query_aware"):
                indices = _uniform_indices(total, count)
            elif strategy == "scene_change":
                indices = _detect_scene_changes(video_path, count, total)
            else:
                raise ValueError(f"Unknown strategy: {strategy!r}")

            frame_metas = _save_frames(
                backend, reader, indices, fps, out_dir,
                image_quality=cfg.perception.image_quality,
            )
            session.register_frames(frame_metas)

            return json.dumps({
                "frame_ids":    [f.frame_id for f in frame_metas],
                "timestamps":   [f.timestamp for f in frame_metas],
                "total_cached": len(session.cached_frames),
            })

        # ── mock fallback (no video file) ─────────────────────────────────
        import random
        from src.memory.session import FrameMeta

        mock_duration = cfg.mock.video_duration
        if strategy in ("uniform", "query_aware"):
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
