"""
Tests for the ReAct Agent factory.

These tests verify agent construction and tool wiring —
not the quality of LLM-generated answers.
"""
from __future__ import annotations

import json
import re

import pytest

from src.agents.react_agent import build_agent
from src.config import get_settings
from src.memory.session import VideoSession

# each build_agent iteration = up to 3 graph steps; matches main.py._get_recursion_limit
_MOCK_RECURSION_LIMIT = 13


def _tool_names(messages: list) -> list[str]:
    return [getattr(m, "name", "") for m in messages if getattr(m, "type", "") == "tool"]


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


# ── Mock-mode guards ──────────────────────────────────────────────────────────
# The mock used to return a canned answer that fabricated scene-graph evidence
# and bypassed every tool (bind_tools -> self). These tests are the contract
# that keeps the offline mock honest: it must drive the real tool loop and must
# never emit fabricated evidence.


def test_mock_agent_exercises_tool_loop(session: VideoSession) -> None:
    """Mock must actually run tools, not short-circuit the agent loop."""
    agent = build_agent(session, use_mock=True)
    result = agent.invoke(
        {"messages": [("user", "what happens?")]},
        config={"recursion_limit": _MOCK_RECURSION_LIMIT},
    )
    names = _tool_names(result["messages"])
    assert "extract_keyframes" in names
    assert "query_scene_graph" in names
    # tools genuinely executed and mutated the shared session
    assert len(session.cached_frames) > 0


def test_mock_answer_is_labeled_and_fabrication_free(session: VideoSession) -> None:
    """Final answer must be clearly labeled [MOCK] and cite no fake evidence."""
    agent = build_agent(session, use_mock=True)
    result = agent.invoke(
        {"messages": [("user", "what happens?")]},
        config={"recursion_limit": _MOCK_RECURSION_LIMIT},
    )
    answer = result["messages"][-1].content
    assert "[MOCK]" in answer
    # no scene-graph triplet of the form "--[relation]-->" (the old fabrication)
    assert re.search(r"--\[.+\]-->", answer) is None


def test_mock_agent_survives_multiple_turns(session: VideoSession) -> None:
    """Interactive mode reuses one agent across turns; the script must replay."""
    agent = build_agent(session, use_mock=True)
    for _ in range(2):
        result = agent.invoke(
            {"messages": [("user", "what happens?")]},
            config={"recursion_limit": _MOCK_RECURSION_LIMIT},
        )
        assert "[MOCK]" in result["messages"][-1].content


def test_mock_is_opt_in() -> None:
    """Default config must not silently route real runs through the mock."""
    assert get_settings().agent.use_mock is False


# ── v2 wiring guards (pure functions, no API needed) ──────────────────────────


def test_v2_recursion_limit_is_wider() -> None:
    """v2 must get the wider budget (iters*5+10); v1 keeps iters*3+1.

    Regression guard: main.py once used the v1 formula for the v2 path, which
    can hit GraphRecursionError mid-answer. Matches _answer_agent_v2 in
    src/eval/run_benchmark.py.
    """
    from main import _get_recursion_limit

    class _Stub:
        _va_max_iterations = 6

    stub = _Stub()
    assert _get_recursion_limit(stub, v2=True) == 40
    assert _get_recursion_limit(stub, v2=False) == 19


def test_pseudo_call_detection() -> None:
    """Detect bare textual tool-calls without flagging real answers or [MOCK]."""
    from src.agents.react_agent import _MOCK_ANSWER, looks_like_pseudo_call

    assert looks_like_pseudo_call("search_memory('what is he holding')") is True
    assert looks_like_pseudo_call("explore_segment(0, 30)") is True
    assert looks_like_pseudo_call("The man cracks eggs into a bowl.") is False
    assert looks_like_pseudo_call("") is False
    assert looks_like_pseudo_call(_MOCK_ANSWER) is False
