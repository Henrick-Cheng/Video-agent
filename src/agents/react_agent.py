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
你是专业的视频内容分析助手。请使用所提供的工具，准确高效地回答关于视频内容的问题。

你拥有一个时序场景图作为结构化工作记忆，存储格式为三元组：
(subject) --[relation]--> (object) @ [t_start, t_end]

决策策略（按顺序执行，避免不必要的 VLM 调用）：
1. 若尚未提取帧 → 先调用 extract_keyframes
2. 在最相关的帧上调用 build_scene_graph 构建场景图
3. 调用 query_scene_graph 检索结构化事实（快速、零额度）
4. 仅当场景图无法回答时（如识别文字、精确计数、细粒度空间关系）才调用 inspect_frame

获得足够信息后，给出简洁准确的中文回答。"""


# ── Factory ───────────────────────────────────────────────────────────────────

def build_agent(
    session: "VideoSession",
    use_mock: bool = False,
    max_iterations: int | None = None,
    verbose: bool | None = None,
) -> Any:
    """
    Create a ReAct agent (CompiledStateGraph) bound to the given VideoSession.

    All four tools are bound to `session` via closure so they share state
    automatically without explicit message passing.

    Parameters
    ----------
    session        : VideoSession providing shared state across all tool calls.
    use_mock       : If True, use a FakeListChatModel — no model server required.
    max_iterations : Hard cap on tool-call rounds (defaults to config value).
    verbose        : Debug logging (defaults to config value).

    Returns
    -------
    CompiledStateGraph — invoke with:
        result = agent.invoke({"messages": [("user", "question")]})
        answer = result["messages"][-1].content
    """
    from src.config import get_settings
    cfg = get_settings()

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
        debug=verbose if verbose is not None else cfg.agent.verbose,
    )


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _get_real_llm():
    """ChatOpenAI pointing to the active LLM endpoint (DashScope or vLLM)."""
    from src.perception.vl_client import get_llm_client
    return get_llm_client()


def _get_mock_llm():
    """FakeListChatModel for testing without a running model server."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    return FakeListChatModel(responses=[
        "根据场景图分析：视频中有一名穿红色外套的人正在骑蓝色自行车穿过路口，交通灯显示绿灯。"
    ])
