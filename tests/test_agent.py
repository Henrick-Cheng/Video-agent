"""
Tests for the ReAct Agent factory.

These tests verify agent construction and tool wiring —
not the quality of LLM-generated answers.
"""
from __future__ import annotations

import json

import pytest

from src.agents.react_agent import build_agent
from src.memory.session import VideoSession


@pytest.fixture
def session() -> VideoSession:
    return VideoSession("test.mp4")


def test_build_agent_returns_something(session: VideoSession) -> None:
    agent = build_agent(session, use_mock=True)
    assert agent is not None


def test_build_agent_has_bound_tools(session: VideoSession) -> None:
    """The compiled graph exposes its tools via the nodes graph."""
    agent = build_agent(session, use_mock=True)
    # LangGraph CompiledStateGraph — just verify it has graph structure
    assert hasattr(agent, "invoke")
    assert hasattr(agent, "nodes")


def test_tools_share_session(session: VideoSession) -> None:
    """
    Verify that all tools operate on the same session instance.
    We test this by invoking the extract_keyframes tool directly (bypassing the LLM)
    and confirming the session state is mutated.
    """
    from src.tools.keyframe import make_extract_keyframes

    tool = make_extract_keyframes(session)
    result = json.loads(tool.invoke({"strategy": "uniform", "count": 4}))

    assert len(session.cached_frames) == 4
    assert result["total_cached"] == 4


def test_all_four_tools_importable() -> None:
    """Smoke test: all tool factories import and construct without error."""
    from src.tools.frame_inspector import make_inspect_frame
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph
    from src.tools.scene_graph_query import make_query_scene_graph

    s = VideoSession("test.mp4")
    tools = [
        make_extract_keyframes(s),
        make_build_scene_graph(s),
        make_query_scene_graph(s),
        make_inspect_frame(s),
    ]
    names = {t.name for t in tools}
    assert names == {
        "extract_keyframes",
        "build_scene_graph",
        "query_scene_graph",
        "inspect_frame",
    }
