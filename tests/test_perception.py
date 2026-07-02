"""
Perception integration tests.

These tests require real resources and are skipped automatically when unavailable:
  - @video_available : data/videos/test1.mp4 must exist
  - @vllm_required   : vLLM VL server must be running on VLM_BASE_URL

Run with all resources:
    VLM_BASE_URL=http://localhost:8001/v1 pytest tests/test_perception.py -v

Run only mock-safe tests:
    pytest tests/test_perception.py -v -m "not vllm"
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# ── test resource markers ─────────────────────────────────────────────────────

TEST_VIDEO = Path(__file__).parent.parent / "data" / "videos" / "test1.mp4"
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:8001/v1")


def _vllm_running() -> bool:
    try:
        import httpx
        r = httpx.get(f"{VLM_BASE_URL}/models", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


video_available = pytest.mark.skipif(
    not TEST_VIDEO.exists(),
    reason=f"test video not found: {TEST_VIDEO} — place a short MP4 there to run this test",
)
vllm_required = pytest.mark.skipif(
    not _vllm_running(),
    reason=f"vLLM VL server not reachable at {VLM_BASE_URL} — run scripts/start_vllm_vl.sh",
)


# ── VLClient unit tests (no video needed, but vLLM must be up) ────────────────

@pytest.mark.vllm
@vllm_required
@video_available
def test_vl_client_caption(tmp_path):
    """VLClient.caption_frame returns non-empty string for a real frame."""
    from src.perception.vl_client import VLClient
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    result = json.loads(extract.invoke({"strategy": "uniform", "count": 1}))
    frame_path = list(session.cached_frames.values())[0].path

    client = VLClient(base_url=VLM_BASE_URL)
    caption = client.caption_frame(frame_path)

    assert isinstance(caption, str)
    assert len(caption) > 10


@pytest.mark.vllm
@vllm_required
@video_available
def test_vl_client_extract_entities():
    """VLClient.extract_entities returns a list of entity dicts."""
    from src.perception.vl_client import VLClient
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    extract.invoke({"strategy": "uniform", "count": 1})
    frame_path = list(session.cached_frames.values())[0].path

    client = VLClient(base_url=VLM_BASE_URL)
    entities = client.extract_entities(frame_path)

    assert isinstance(entities, list)
    if entities:
        assert "name" in entities[0]
        assert "type" in entities[0]


@pytest.mark.vllm
@vllm_required
@video_available
def test_vl_client_inspect():
    """VLClient.inspect returns structured answer + entities + relations."""
    from src.perception.vl_client import VLClient
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    extract.invoke({"strategy": "uniform", "count": 1})
    frame_path = list(session.cached_frames.values())[0].path

    client = VLClient(base_url=VLM_BASE_URL)
    result = client.inspect(frame_path, "What objects are visible in this scene?")

    assert "answer" in result
    assert "entities_found" in result
    assert "relations_found" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 5
    assert isinstance(result["entities_found"], list)
    assert isinstance(result["relations_found"], list)


# ── extract_keyframes real video tests ────────────────────────────────────────

@video_available
def test_extract_keyframes_uniform_real():
    """Uniform extraction creates real JPEG files and registers them."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    tool = make_extract_keyframes(session)
    result = json.loads(tool.invoke({"strategy": "uniform", "count": 4}))

    assert len(result["frame_ids"]) == 4
    assert result["total_cached"] == 4
    assert len(session.cached_frames) == 4

    # all frame_ids follow timestamp format
    for fid in result["frame_ids"]:
        assert fid.startswith("t_"), f"unexpected frame_id format: {fid}"

    # all files exist on disk
    for meta in session.cached_frames.values():
        assert meta.path is not None
        assert Path(meta.path).exists(), f"frame not saved: {meta.path}"


@video_available
def test_extract_keyframes_scene_change_real():
    """Scene-change extraction (or uniform fallback) runs without error."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    tool = make_extract_keyframes(session)
    result = json.loads(tool.invoke({"strategy": "scene_change", "count": 4}))

    assert result["total_cached"] > 0


@video_available
def test_extract_keyframes_timestamps_monotone():
    """Extracted timestamps should be strictly increasing for uniform strategy."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes

    session = VideoSession(str(TEST_VIDEO))
    tool = make_extract_keyframes(session)
    result = json.loads(tool.invoke({"strategy": "uniform", "count": 6}))

    ts = result["timestamps"]
    assert ts == sorted(ts), "timestamps not monotonically increasing"


# ── inspect_frame real integration test ───────────────────────────────────────

@video_available
@pytest.mark.vllm
@vllm_required
def test_inspect_frame_real_updates_scene_graph():
    """inspect_frame calls VLM, back-propagates entities to scene graph."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.frame_inspector import make_inspect_frame

    session = VideoSession(str(TEST_VIDEO))

    # first extract some frames so timestamps are real
    extract = make_extract_keyframes(session)
    extract.invoke({"strategy": "uniform", "count": 4})

    first_ts = list(session.cached_frames.values())[0].timestamp
    graph_size_before = len(session.scene_graph)

    inspect = make_inspect_frame(session)
    result = json.loads(inspect.invoke({
        "timestamp": first_ts,
        "question": "What objects and people are visible in this frame?",
    }))

    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 5
    assert result["frame_id"] is not None

    # scene graph should grow if VLM found anything
    # (not guaranteed — VLM output may parse to empty lists)
    assert len(session.scene_graph) >= graph_size_before


def test_inspect_frame_mock_fallback_updates_graph(mock_mode):
    """
    In explicit offline mode, inspect_frame returns honest synthetic data
    and still back-propagates to the scene graph.
    """
    from src.memory.session import VideoSession, FrameMeta
    from src.tools.frame_inspector import make_inspect_frame

    session = VideoSession("/nonexistent/video.mp4")
    # register a frame with no path (offline mode)
    session.register_frames([FrameMeta("t_00030.00", timestamp=30.0, path=None)])

    inspect = make_inspect_frame(session)
    result = json.loads(inspect.invoke({
        "timestamp": 30.0,
        "question": "What is happening?",
    }))

    assert "[MOCK]" in result["answer"]
    assert result["frame_id"] == "t_00030.00"
    assert len(result["new_entities"]) > 0
    assert len(session.scene_graph) > 0
