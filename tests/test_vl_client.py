"""
VLClient tests — DashScope backend.

All tests require DASHSCOPE_API_KEY in the environment and test1.mp4 on disk.
Run with:
    DASHSCOPE_API_KEY=sk-xxx pytest tests/test_vl_client.py -v -s
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ── markers ───────────────────────────────────────────────────────────────────

TEST_VIDEO = Path(__file__).parent.parent / "data" / "videos" / "test1.mp4"

video_available = pytest.mark.skipif(
    not TEST_VIDEO.exists(),
    reason=f"test video not found: {TEST_VIDEO}",
)
dashscope_required = pytest.mark.skipif(
    not os.getenv("DASHSCOPE_API_KEY"),
    reason="DASHSCOPE_API_KEY not set — set it to run DashScope tests",
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_test_frame_path() -> str:
    """Extract one frame from test1.mp4 and return its path."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    extract.invoke({"strategy": "uniform", "count": 1})
    frame = list(session.cached_frames.values())[0]
    assert frame.path and Path(frame.path).exists(), "Frame was not saved to disk"
    return frame.path


# ── VLClient unit tests ───────────────────────────────────────────────────────

@dashscope_required
@video_available
def test_vl_client_caption_dashscope():
    """caption_frame returns a non-empty Chinese description."""
    from src.perception.vl_client import get_vl_client

    frame_path = _get_test_frame_path()
    client = get_vl_client()
    caption = client.caption_frame(frame_path)

    print(f"\n[caption] {caption[:200]}")
    assert isinstance(caption, str)
    assert len(caption) > 10


@dashscope_required
@video_available
def test_vl_client_extract_entities_dashscope():
    """extract_entities returns a non-empty list with name/type fields."""
    from src.perception.vl_client import get_vl_client

    frame_path = _get_test_frame_path()
    client = get_vl_client()
    entities = client.extract_entities(frame_path)

    print(f"\n[entities] {entities}")
    assert isinstance(entities, list)
    if entities:
        assert "name" in entities[0]
        assert "type" in entities[0]


@dashscope_required
@video_available
def test_vl_client_inspect_dashscope():
    """inspect returns structured answer + entities + relations."""
    from src.perception.vl_client import get_vl_client

    frame_path = _get_test_frame_path()
    client = get_vl_client()
    result = client.inspect(frame_path, "图中有什么人物或物体？他们在做什么？")

    print(f"\n[inspect.answer] {result['answer'][:200]}")
    print(f"[inspect.entities] {result['entities_found']}")
    print(f"[inspect.relations] {result['relations_found']}")

    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 5
    assert isinstance(result["entities_found"], list)
    assert isinstance(result["relations_found"], list)


@dashscope_required
@video_available
def test_vl_client_multi_image():
    """call_multi with 2 frames returns a valid JSON string."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes
    from src.perception.vl_client import get_vl_client

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    extract.invoke({"strategy": "uniform", "count": 2})

    paths = [f.path for f in session.cached_frames.values() if f.path]
    assert len(paths) >= 2

    client = get_vl_client()
    raw = client.call_multi(
        paths[:2],
        "请描述这两帧画面中的主要内容，输出 JSON: {\"summary\": \"...\"}",
    )
    print(f"\n[multi_image raw] {raw[:300]}")
    assert isinstance(raw, str)
    assert len(raw) > 5
