"""Tests for VideoSession shared state management."""
from __future__ import annotations

import pytest

from src.memory.session import FrameMeta, VideoSession


@pytest.fixture
def session() -> VideoSession:
    return VideoSession(video_path="test_video.mp4")


def test_session_creation(session: VideoSession) -> None:
    assert session.video_path == "test_video.mp4"
    assert session.session_id.startswith("sess_")
    assert len(session.cached_frames) == 0
    assert len(session.scene_graph) == 0


def test_register_and_get_frames(session: VideoSession) -> None:
    frames = [FrameMeta(frame_id=f"f{i}", timestamp=float(i * 10)) for i in range(5)]
    session.register_frames(frames)

    assert len(session.cached_frames) == 5
    assert session.get_frame("f2") is not None
    assert session.get_frame("f2").timestamp == 20.0
    assert session.get_frame("nonexistent") is None


def test_get_frame_by_timestamp(session: VideoSession) -> None:
    frames = [FrameMeta(f"f{i}", timestamp=float(i * 10)) for i in range(6)]
    session.register_frames(frames)

    # exact hit
    assert session.get_frame_by_timestamp(30.0, tolerance=0.5).frame_id == "f3"

    # within tolerance
    assert session.get_frame_by_timestamp(31.5, tolerance=2.0).frame_id == "f3"

    # outside tolerance → None
    assert session.get_frame_by_timestamp(35.0, tolerance=2.0) is None

    # empty session
    empty = VideoSession("empty.mp4")
    assert empty.get_frame_by_timestamp(5.0) is None


def test_update_scene_graph_basic(session: VideoSession) -> None:
    nodes = [{"name": "cat",  "type": "animal", "attributes": {"color": "orange"}}]
    edges = [{"subject": "cat", "relation": "on", "object": "mat",
              "t_start": 1.0, "t_end": 3.0, "confidence": 0.9}]

    stats = session.update_scene_graph(nodes, edges)
    assert stats["nodes_added"] == 1
    assert stats["edges_added"] == 1
    assert len(session.scene_graph) == 1


def test_update_scene_graph_deduplication(session: VideoSession) -> None:
    nodes = [{"name": "dog"}]
    edges = [{"subject": "dog", "relation": "sitting", "object": "floor",
              "t_start": 0.0, "t_end": 2.0, "confidence": 0.85}]

    session.update_scene_graph(nodes, edges)
    stats2 = session.update_scene_graph(nodes, edges)

    # duplicate: nothing should be added
    assert stats2["nodes_added"] == 0
    assert stats2["edges_added"] == 0
    assert len(session.scene_graph) == 1


def test_update_scene_graph_attribute_merge(session: VideoSession) -> None:
    session.update_scene_graph(
        [{"name": "person", "type": "person", "attributes": {"clothing": "red"}}], []
    )
    session.update_scene_graph(
        [{"name": "person", "attributes": {"age_group": "adult"}}], []
    )
    entity = session.scene_graph.entities["person"]
    assert entity.attributes["clothing"] == "red"
    assert entity.attributes["age_group"] == "adult"


def test_get_subgraph(session: VideoSession) -> None:
    session.update_scene_graph(
        new_nodes=[{"name": "person"}, {"name": "bicycle"}, {"name": "road"}],
        new_edges=[
            {"subject": "person",  "relation": "riding",
             "object": "bicycle", "t_start": 0.0, "t_end": 5.0},
            {"subject": "bicycle", "relation": "on",
             "object": "road",    "t_start": 0.0, "t_end": 5.0},
        ],
    )
    subgraph = session.get_subgraph(["person"])

    # person → bicycle edge should be included
    assert "person" in subgraph["entities"]
    assert "bicycle" in subgraph["entities"]
    assert any(t["subject"] == "person" for t in subgraph["triplets"])

    # road is not directly connected to person, but is connected to bicycle
    # which appears in the subgraph — implementation may include it
    assert len(subgraph["triplets"]) >= 1


def test_session_summary(session: VideoSession) -> None:
    summary = session.summary()
    assert "test_video.mp4" in summary
    assert "frames=0" in summary
