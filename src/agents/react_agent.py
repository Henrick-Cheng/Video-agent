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
You are a professional video content analysis assistant. Use the provided tools to \
answer questions about the video content accurately and efficiently.

You have a temporal scene graph as structured working memory, stored as triplets:
(subject) --[relation]--> (object) @ [t_start, t_end]

[Decision strategy — follow strictly in order to avoid wasting API calls]
1. If frames have not been extracted yet → call extract_keyframes first
2. Call build_scene_graph on the most relevant frames (process only the frames you need)
3. Call query_scene_graph to retrieve structured facts (fast, zero-cost — use it first)
4. Only when the scene graph cannot answer (e.g. reading text, exact counting, \
fine-grained attributes) call inspect_frame

[Answering principles]
- The final answer must be evidence-backed: cite scene graph triplets \
(e.g. "(A) --[riding]--> (B) @ [0.0s, 3.0s]") or specific timestamps
- inspect_frame updates the scene graph automatically; when it returns \
nodes_added_to_graph > 0 you may call query_scene_graph again to fetch the new content"""


# ── Factory ───────────────────────────────────────────────────────────────────

def build_agent(
    session: "VideoSession",
    use_mock: bool = False,
    max_iterations: int | None = None,
    verbose: bool | None = None,
    system_prompt: str | None = None,
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
    system_prompt  : Override the default system prompt. The benchmark passes a
                     short-answer variant so the agent emits a terse final answer
                     (the interactive product keeps the evidence-citing default).

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
    agent = create_agent(llm, tools,
                         system_prompt=system_prompt or _SYSTEM_PROMPT, debug=False)

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
            "Based on the scene graph: a person in a red jacket is riding a blue "
            "bicycle through an intersection, and the traffic light is green. "
            "Evidence: (person_A) --[riding]--> (bicycle) @ [0.0s, 3.0s]"
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
