"""
ReAct Agent factory for video understanding.

Uses LangChain 1.x create_agent (backed by LangGraph) — the current stable API.
LangGraph is already a dependency of LangChain 1.x so there is no extra package.

Invocation:
    agent = build_agent(session)
    result = agent.invoke({"messages": [("user", "your question")]})
    answer = result["messages"][-1].content

Trace extraction:
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            # tool call step
        elif getattr(msg, "type", None) == "tool":
            # tool observation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from src.tools.frame_inspector import make_inspect_frame
from src.tools.keyframe import make_extract_keyframes
from src.tools.scene_graph_builder import make_build_scene_graph
from src.tools.scene_graph_query import make_query_scene_graph

if TYPE_CHECKING:
    from src.memory.session import VideoSession

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
你是专业的视频内容分析助手。请使用所提供的工具，准确高效地回答关于视频内容的问题。

你拥有一个时序场景图作为结构化工作记忆，存储格式为三元组：
(subject) --[relation]--> (object) @ [t_start, t_end]

【决策策略 — 严格按顺序，避免浪费 API 调用】
1. 若尚未提取帧 → 先调用 extract_keyframes
2. 在最相关的帧上调用 build_scene_graph 构建场景图（只处理必要帧）
3. 调用 query_scene_graph 检索结构化事实（快速、零成本，优先使用）
4. 仅当场景图无法回答时（如识别文字、精确计数、细粒度属性）才调用 inspect_frame

【回答原则】
- 最终答案必须有证据：引用场景图三元组（如"(A) --[骑乘]--> (B) @ [0.0s, 3.0s]"）或具体时间戳
- inspect_frame 会自动更新场景图；返回 nodes_added_to_graph > 0 时可再次 query_scene_graph 获取新内容"""


# ── Factory ───────────────────────────────────────────────────────────────────

def build_agent(
    session: "VideoSession",
    use_mock: bool = False,
    max_iterations: int | None = None,
    verbose: bool | None = None,
) -> Any:
    """
    Create a LangChain 1.x ReAct agent (CompiledStateGraph) bound to the session.

    All four tools share `session` via closure — no message passing needed.

    Parameters
    ----------
    session        : VideoSession providing shared state across all tool calls.
    use_mock       : If True, use a mock LLM that skips all tool calls.
    max_iterations : Stored as recursion_limit for LangGraph (pass at invoke time).
    verbose        : Enable debug-level step logging in LangGraph.

    Returns
    -------
    CompiledStateGraph — invoke with:
        result = agent.invoke({"messages": [("user", "question")]},
                              config={"recursion_limit": 13})
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
    _iters = max_iterations if max_iterations is not None else cfg.agent.max_iterations

    # debug=False: LangGraph's internal [values]/[updates] log is too verbose;
    # callers (main.py) handle trace display by inspecting result["messages"].
    agent = create_agent(llm, tools, system_prompt=_SYSTEM_PROMPT, debug=False)

    # Attach resolved config so main.py / tests can read it
    agent._va_max_iterations = _iters  # type: ignore[attr-defined]
    return agent


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _get_real_llm():
    """ChatOpenAI pointing to the active LLM endpoint (DashScope or vLLM)."""
    from src.perception.vl_client import get_llm_client
    return get_llm_client()


def _get_mock_llm() -> BaseChatModel:
    """
    A minimal mock ChatModel for offline testing.

    Overrides bind_tools to bypass tool-calling and immediately returns a
    preset final answer as a plain AIMessage.
    """
    class _DirectAnswerModel(BaseChatModel):
        response: str = (
            "根据场景图分析：视频中有一名穿红色外套的人正在骑蓝色自行车穿过路口，"
            "交通灯显示绿灯。证据：(person_A) --[骑乘]--> (bicycle) @ [0.0s, 3.0s]"
        )

        def _generate(
            self,
            messages: list,
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> ChatResult:
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=self.response))]
            )

        @property
        def _llm_type(self) -> str:
            return "direct_answer_mock"

        def bind_tools(self, tools: list, **kwargs: Any) -> "_DirectAnswerModel":  # type: ignore[override]
            return self  # ignore tools; always return the preset answer

    return _DirectAnswerModel()
