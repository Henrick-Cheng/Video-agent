"""
ReAct Agent factory for video understanding.

The Agent uses a scene graph as working memory and decides in each step
which tool to call, with what arguments, and in what order.

LangChain 1.x uses `create_agent` from `langchain.agents` (backed by LangGraph).
The returned object is a CompiledStateGraph.

Invocation:
    result = agent.invoke({"messages": [("user", "your question")]})
    final_answer = result["messages"][-1].content
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent

from src.tools.keyframe import make_extract_keyframes
from src.tools.scene_graph_builder import make_build_scene_graph
from src.tools.scene_graph_query import make_query_scene_graph
from src.tools.frame_inspector import make_inspect_frame

if TYPE_CHECKING:
    from src.memory.session import VideoSession

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert video analysis assistant. Answer questions about video content
accurately and efficiently using the tools available.

You have access to a temporal scene graph as structured working memory.
It stores facts as triplets: (subject) --[relation]--> (object) @ [t_start, t_end].

Decision strategy — follow this order to minimize expensive VLM calls:
1. If no frames have been extracted yet → call extract_keyframes first.
2. Call build_scene_graph on the most relevant frames.
3. Call query_scene_graph to retrieve structured facts (fast, free).
4. Call inspect_frame ONLY when the scene graph lacks sufficient detail
   (e.g., reading text, counting objects, fine-grained spatial reasoning).

When you have enough information, provide a concise, factual answer."""


# ── Factory ───────────────────────────────────────────────────────────────────

def build_agent(
    session: "VideoSession",
    use_mock: bool = False,
    max_iterations: int = 10,
    verbose: bool = True,
) -> Any:
    """
    Create a ReAct agent (CompiledStateGraph) bound to the given VideoSession.

    All four tools are bound to `session` via closure so they share state
    automatically without any explicit message passing.

    Parameters
    ----------
    session        : VideoSession providing shared state across all tool calls.
    use_mock       : If True, use a FakeListChatModel — no vLLM server required.
    max_iterations : Hard cap on tool-call rounds (passed to recursion_limit).
    verbose        : Unused in LangGraph mode; set debug=True in create_agent instead.

    Returns
    -------
    CompiledStateGraph
        Invoke with:
            result = agent.invoke({"messages": [("user", "your question")]})
            answer = result["messages"][-1].content

        Intermediate tool calls are in result["messages"] as ToolMessage objects.
    """
    tools = [
        make_extract_keyframes(session),
        make_build_scene_graph(session),
        make_query_scene_graph(session),
        make_inspect_frame(session),
    ]

    llm = _get_mock_llm() if use_mock else _get_real_llm()

    return create_agent(
        llm,
        tools,
        system_prompt=SYSTEM_PROMPT,
        debug=verbose,
    )


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _get_real_llm():
    """ChatOpenAI pointing to a local vLLM server running Qwen3-8B."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "Qwen/Qwen3-8B"),
        base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("VLLM_API_KEY", "token-abc"),
        temperature=0.1,
        max_tokens=2048,
    )


def _get_mock_llm():
    """
    FakeListChatModel for testing without a running vLLM server.
    Returns strings that LangChain treats as AI messages (no real tool calls).
    Use the manual pipeline in examples/demo.py for full end-to-end testing.
    """
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    return FakeListChatModel(responses=[
        "The video shows a person in a red jacket riding a blue bicycle "
        "through an intersection while the traffic light is green."
    ])
