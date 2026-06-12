"""
Local ASR transcription for the L0 memory layer.

Uses faster-whisper (CTranslate2, CPU int8) — zero API cost. The transcript is
part of the lazy memory's global layer: many benchmark questions ("according
to the video...") are answerable only from narration, which a vision-only
pipeline cannot reach (Phase 13 finding #5).

Graceful degradation: if faster-whisper is not installed or the video has no
usable audio track, returns [] and the pipeline continues vision-only.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_SIZE = "small"


def _get_model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        logger.info("Loading faster-whisper '%s' (first call downloads weights)",
                    _MODEL_SIZE)
        _MODEL = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")
    return _MODEL


def _cache_path(video_path: str):
    from pathlib import Path
    p = Path(video_path)
    cache_dir = Path("data/asr_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        size = p.stat().st_size
    except OSError:
        size = 0
    return cache_dir / f"{p.stem}.{size}.{_MODEL_SIZE}.json"


def transcribe(video_path: str, language: Optional[str] = None) -> list[dict]:
    """
    Transcribe the audio track of *video_path* (file-cached: transcription is
    deterministic per video+model, and benchmark methods would otherwise
    re-transcribe the same video once per method).

    Returns
    -------
    [{"t_start": float, "t_end": float, "text": str}, ...] — empty list when
    ASR is unavailable or the video has no speech.
    """
    import json as _json

    cache = _cache_path(video_path)
    if cache.exists():
        try:
            return _json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        model = _get_model()
    except ImportError:
        logger.warning("faster-whisper not installed — transcript unavailable "
                       "(pip install faster-whisper)")
        return []

    try:
        segments, _info = model.transcribe(
            video_path, language=language, vad_filter=True)
        out = [
            {"t_start": round(s.start, 1), "t_end": round(s.end, 1),
             "text": s.text.strip()}
            for s in segments
            if s.text.strip()
        ]
        logger.info("ASR: %d segments from %s", len(out), video_path)
        return out
    except Exception as exc:
        logger.warning("ASR failed for %s: %s — continuing vision-only",
                       video_path, exc)
        return []


def transcript_text(transcript: list[dict],
                    t_start: Optional[float] = None,
                    t_end: Optional[float] = None,
                    max_chars: int = 4000) -> str:
    """Render (a time window of) a transcript as timestamped lines."""
    rows = transcript
    if t_start is not None or t_end is not None:
        lo = t_start if t_start is not None else float("-inf")
        hi = t_end if t_end is not None else float("inf")
        rows = [r for r in transcript if r["t_end"] >= lo and r["t_start"] <= hi]
    if not rows:
        return ""
    lines = [f"[{r['t_start']:.0f}-{r['t_end']:.0f}s] {r['text']}" for r in rows]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... transcript truncated ...]"
    return text
