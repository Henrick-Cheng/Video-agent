"""Tests for the 4 Agent tools in mock mode."""
from __future__ import annotations

import json

import pytest

from src.memory.session import FrameMeta, VideoSession
from src.tools.frame_inspector import make_inspect_frame
from src.tools.keyframe import make_extract_keyframes
from src.tools.scene_graph_builder import make_build_scene_graph
from src.tools.scene_graph_query import make_query_scene_graph


@pytest.fixture
def session() -> VideoSession:
    return VideoSession(video_path="test.mp4")


# ── extract_keyframes ─────────────────────────────────────────────────────────

def test_extract_keyframes_uniform(session: VideoSession) -> None:
    tool = make_extract_keyframes(session)
    result = json.loads(tool.invoke({"strategy": "uniform", "count": 8}))

    assert len(result["frame_ids"]) == 8
    assert len(result["timestamps"]) == 8
    assert result["total_cached"] == 8
    assert len(session.cached_frames) == 8


def test_extract_keyframes_accumulates(session: VideoSession) -> None:
    tool = make_extract_keyframes(session)
    tool.invoke({"strategy": "uniform", "count": 4})
    result = json.loads(tool.invoke({"strategy": "scene_change", "count": 4}))

    # second call adds to the cache (different frame_ids due to different timestamps)
    assert result["total_cached"] >= 4


def test_extract_keyframes_has_tool_metadata(session: VideoSession) -> None:
    tool = make_extract_keyframes(session)
    assert tool.name == "extract_keyframes"
    assert tool.description  # LangChain exposes docstring here


# ── build_scene_graph ─────────────────────────────────────────────────────────

@pytest.fixture
def session_with_frames() -> VideoSession:
    s = VideoSession("test.mp4")
    frames = [FrameMeta(f"f{i}", timestamp=float(i * 15)) for i in range(4)]
    s.register_frames(frames)
    return s


def test_build_scene_graph(session_with_frames: VideoSession, mock_mode) -> None:
    tool = make_build_scene_graph(session_with_frames)
    frame_ids = ",".join(session_with_frames.cached_frames.keys())
    result = json.loads(tool.invoke({"frame_ids": frame_ids, "focus_entities": ""}))

    assert "new_triplets" in result
    assert "graph_summary" in result
    assert result["edges_added"] >= 0
    assert len(session_with_frames.scene_graph) > 0


def test_build_scene_graph_wildcard(session_with_frames: VideoSession, mock_mode) -> None:
    tool = make_build_scene_graph(session_with_frames)
    result = json.loads(tool.invoke({"frame_ids": "*", "focus_entities": "person"}))
    assert len(session_with_frames.scene_graph) > 0


def test_build_scene_graph_mock_is_honest(session_with_frames: VideoSession, mock_mode) -> None:
    """Offline mock output must be labeled and never look like real VLM evidence."""
    tool = make_build_scene_graph(session_with_frames)
    raw = tool.invoke({"frame_ids": "*", "focus_entities": ""})
    result = json.loads(raw)

    assert result["_mode"] == "mock"
    # the old fabrication ("person_A", source="vlm") must be gone
    assert "person_A" not in raw
    assert "red jacket" not in raw
    assert '"source": "vlm"' not in raw
    # synthetic entities are unmistakably mock
    assert all(t["subject"].startswith("mock") for t in result["new_triplets"])


def test_build_scene_graph_fails_loud_without_backend(session_with_frames: VideoSession) -> None:
    """Real run (mock disabled) with no frames on disk must error, not fabricate."""
    # frames in the fixture have no disk path; mock stays disabled here
    tool = make_build_scene_graph(session_with_frames)
    raw = tool.invoke({"frame_ids": "*", "focus_entities": ""})
    result = json.loads(raw)

    assert result["_mode"] == "error"
    assert result["nodes_added"] == 0
    assert len(session_with_frames.scene_graph) == 0
    assert "person_A" not in raw  # no fabricated evidence leaked


# ── query_scene_graph ─────────────────────────────────────────────────────────

def test_query_empty_graph(session: VideoSession) -> None:
    tool = make_query_scene_graph(session)
    result = json.loads(tool.invoke({"question": "What is the person doing?"}))

    assert result["found"] is False
    assert "empty" in result["entity_summary"].lower()


def test_query_with_data(session: VideoSession) -> None:
    session.update_scene_graph(
        new_nodes=[{"name": "person"}, {"name": "bicycle"}],
        new_edges=[
            {
                "subject": "person", "relation": "riding",
                "object": "bicycle", "t_start": 5.0, "t_end": 15.0,
                "confidence": 0.9,
            }
        ],
    )
    tool = make_query_scene_graph(session)
    result = json.loads(tool.invoke({"question": "What is the person doing?"}))

    assert result["found"] is True
    assert len(result["triplets"]) >= 1
    assert result["triplets"][0]["relation"] == "riding"


def test_query_entity_summary(session: VideoSession) -> None:
    session.update_scene_graph(
        [{"name": "cat"}, {"name": "sofa"}],
        [{"subject": "cat", "relation": "on", "object": "sofa",
          "t_start": 0.0, "t_end": 1.0}],
    )
    tool = make_query_scene_graph(session)
    result = json.loads(tool.invoke({"question": "general query"}))
    assert "cat" in result["entity_summary"] or "sofa" in result["entity_summary"]


# ── inspect_frame ─────────────────────────────────────────────────────────────

def test_inspect_no_cached_frames(session: VideoSession) -> None:
    tool = make_inspect_frame(session)
    result = json.loads(tool.invoke({"timestamp": 30.0, "question": "What is happening?"}))

    assert "No frames" in result["answer"]
    assert result["frame_id"] is None


def test_inspect_back_propagates_entities(session: VideoSession, mock_mode) -> None:
    session.register_frames([FrameMeta("f30", timestamp=30.0, extracted=True)])
    graph_size_before = len(session.scene_graph)

    tool = make_inspect_frame(session)
    result = json.loads(tool.invoke({"timestamp": 30.0, "question": "Who is on the sidewalk?"}))

    assert result["frame_id"] == "f30"
    assert result["timestamp_used"] == pytest.approx(30.0, abs=0.1)
    assert len(result["new_entities"]) > 0
    assert len(session.scene_graph) > graph_size_before  # back-propagation


def test_inspect_frame_fallback(session: VideoSession, mock_mode) -> None:
    # register a frame at ts=50, request ts=30 with tight tolerance
    session.register_frames([FrameMeta("f50", timestamp=50.0, extracted=True)])

    tool = make_inspect_frame(session)
    # tolerance in mock is 5s, so ts=30 → 50 is 20s away → should fall back
    result = json.loads(tool.invoke({"timestamp": 30.0, "question": "What is here?"}))
    # mock falls back to any available frame
    assert result["frame_id"] is not None


def test_inspect_mock_is_honest(session: VideoSession, mock_mode) -> None:
    """Offline inspect output must be labeled and free of fabricated evidence."""
    session.register_frames([FrameMeta("f30", timestamp=30.0, extracted=True)])
    tool = make_inspect_frame(session)
    raw = tool.invoke({"timestamp": 30.0, "question": "What is here?"})
    result = json.loads(raw)

    assert "[MOCK]" in result["answer"]
    assert "red jacket" not in raw
    assert "person_A" not in raw


def test_inspect_fails_loud_without_backend(session: VideoSession) -> None:
    """Real run (mock disabled) on a frame not on disk must error, not fabricate."""
    session.register_frames([FrameMeta("f30", timestamp=30.0, extracted=True)])
    tool = make_inspect_frame(session)
    raw = tool.invoke({"timestamp": 30.0, "question": "What is here?"})
    result = json.loads(raw)

    assert "error" in result
    assert result["new_entities"] == []
    assert "red jacket" not in raw
