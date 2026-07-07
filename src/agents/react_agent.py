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

import json
import re
from itertools import cycle
from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

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


# ── Pseudo-call detection ─────────────────────────────────────────────────────
# A final message that is just "word(...)" — the model emitted a textual pseudo
# tool-call instead of using the tool-calling interface. Shared by the benchmark
# (run_benchmark._answer_agent_v2) and the product CLI (main._invoke_v2_with_retry).
PSEUDO_CALL_RE = re.compile(r"^\s*\w+\s*\(.{0,400}\)\s*$", re.DOTALL)


def looks_like_pseudo_call(text: str) -> bool:
    """True if `text` looks like a bare textual tool-call rather than an answer."""
    return bool(text) and bool(PSEUDO_CALL_RE.match(text))


def get_recursion_limit(agent: Any, v2: bool = False) -> int:
    """Derive LangGraph recursion_limit from the agent's stored max_iterations.

    v2's confidence loop (search + up to 3 rounds x 2 explore + inspect) needs a
    wider budget than v1's linear loop; matches _answer_agent_v2 in
    src/eval/run_benchmark.py so product/API paths can't hit GraphRecursionError
    on a run the benchmark would complete.
    """
    iters = getattr(agent, "_va_max_iterations", 6)
    return iters * 5 + 10 if v2 else iters * 3 + 1


def invoke_with_retry(agent: Any, user_text: str, recursion_limit: int,
                      on_retry: Any = None) -> dict:
    """Invoke the agent once; if the final message is a textual pseudo tool-call
    rather than an answer, re-ask once with a corrective instruction.

    v2 models sometimes emit e.g. `search_memory("...")` as plain text instead
    of calling the tool. Mirrors the benchmark's retry (run_benchmark.py). The
    [MOCK] placeholder never matches, so the mock/v1 path passes through cleanly.

    on_retry: optional zero-arg callable invoked when the corrective re-ask
    actually fires (the CLI uses it to print a notice).
    """
    result = agent.invoke(
        {"messages": [("user", user_text)]},
        config={"recursion_limit": recursion_limit},
    )
    answer = result["messages"][-1].content
    if looks_like_pseudo_call(answer):
        if on_retry is not None:
            on_retry()
        corrective = (
            f"{user_text}\n\nYour previous reply was plain text that LOOKED like "
            f"a tool call ({answer[:80]}); it was not executed. Either CALL the "
            f"tool through the tool-calling interface, or give your final answer."
        )
        result = agent.invoke(
            {"messages": [("user", corrective)]},
            config={"recursion_limit": recursion_limit},
        )
    return result


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
    use_mock       : If True, use a scripted offline LLM that drives the full
                     tool loop (extract_keyframes -> query_scene_graph) and then
                     returns a clearly-labeled [MOCK] placeholder — it fabricates
                     no video content. For offline smoke tests / no API key.
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


# ── v2: lazy memory + confidence-driven loop ─────────────────────────────────
# Literature template (Stanford/Graph-VideoAgent): answer → self-assess
# confidence 1-3 → gather more evidence only if insufficient, bounded budget.
# Graph construction itself is an agent decision (explore_segment), not a
# preprocessing step.

_V2_SYSTEM_CORE = """\
You are a video question-answering agent. The user message provides: a global \
summary of the video, its duration, the narration transcript (may be empty), \
and the time windows already explored.

[Tools]
- search_memory — free lookup over everything known so far (facts with \
timestamps, notes from explored windows, transcript). Always try this before \
exploring.
- explore_segment — watch a time window closely and add detailed notes + \
facts to memory. Costs one vision call — choose the window deliberately, \
guided by transcript timestamps, the summary, or earlier hits.
- inspect_frame — pixel-level read of a single frame (on-screen text, exact \
counting).

Tools are used ONLY through the tool-calling interface. Plain text in your \
message is treated as your final answer — never write anything that looks \
like a function call.

[Procedure — confidence-driven]
1. You MUST start by CALLING the search_memory tool with the question (it is \
free and shows what is already known).
2. From the search result plus the provided context, privately rate your \
confidence: 1 = insufficient evidence, 2 = partial, 3 = sufficient. If below \
3, gather evidence with explore_segment — at most 2 explorations per round, \
at most 3 rounds in total.
3. Stop as soon as confidence reaches 3 or the budget is spent, then give \
your best-supported answer.

[Window strategy]
- Short video (under ~60s) with nothing explored yet: explore the FULL span \
(t_start=0, t_end=duration) first — one exploration covers everything.
- Duration/order comparisons need the COMPLETE time extent of each activity; \
if a fact's interval touches the edge of an explored window, the activity \
may continue outside it — widen the exploration before comparing durations.

[Grounding rules]
- Never answer from prior knowledge; every claim must trace to the summary, \
transcript, memory, or an explored window.
- The narration transcript is authoritative for why / how / "what is said" / \
reasons / steps / sequence questions — READ IT CAREFULLY (it is provided in \
full above) before exploring or answering; for these, a relevant transcript \
line usually beats a visual window.
- Absence of a fact in memory is NOT evidence of 'no' — the memory only \
covers explored windows. Verify with explore_segment before answering 'no'.
- If evidence is still insufficient after the budget, state what is missing \
instead of guessing."""

_V2_ANSWER_SHORT = """

[Answer format — strict]
Your FINAL message must be ONLY the answer itself: a single word or a short \
phrase. For yes/no questions, answer exactly 'yes' or 'no'. No explanation, \
no timestamps, no extra words in the final message."""

_V2_ANSWER_VERBOSE = """

[Answer format]
Give a concise, accurate answer (1-3 sentences). Mention timestamps when \
relevant."""

# No-explore variant (routing experiment): for reasoning/structural questions
# the data shows zooming into one window LOSES the global picture and hurts.
# Here the agent answers from the global summary + transcript + a free memory
# search, with no window exploration available.
_V2_SYSTEM_NOEXPLORE = """\
You are a video question-answering agent. The user message provides: a global \
summary of the video, its duration, the narration transcript (may be empty), \
and any notes from windows explored for earlier questions.

[Tools]
- search_memory — free lookup over everything known so far (facts with \
timestamps, notes from earlier windows, transcript).

Tools are used ONLY through the tool-calling interface. Plain text in your \
message is treated as your final answer — never write anything that looks \
like a function call.

[Procedure]
1. You MUST start by CALLING the search_memory tool with the question.
2. Answer from the global summary, the transcript, and the search result. \
This is a holistic / reasoning question best answered from the whole-video \
context — do not ask to zoom into a single moment.

[Grounding rules]
- Never answer from prior knowledge; every claim must trace to the summary, \
transcript, or memory.
- The narration transcript is authoritative for why / how / "what is said" / \
reasons / steps / sequence questions — READ IT CAREFULLY (it is provided in \
full above) before answering.
- If the evidence genuinely does not support an answer, say what is missing \
instead of guessing."""


def prepare_l0(session: "VideoSession", verbose: bool = True) -> None:
    """Product-side v2 per-video init: sparse-frame global summary (1 VL call)
    + local ASR transcript. Mirrors the benchmark's _prepare_l0 but without
    token accounting — this is the lightweight upfront cost that replaces v1's
    full-graph prebuild (everything else is built on demand by the agent).

    Idempotent: skips work if the summary/transcript are already populated, so
    interactive mode pays it once and reuses it across questions.
    """
    from src.perception.vl_client import get_vl_client
    from src.perception import asr
    from src.tools.keyframe import make_extract_keyframes

    if session.global_summary and session.transcript is not None \
            and session.duration_sec:
        return  # already prepared (e.g. a later turn in interactive mode)

    from src.tools.keyframe import _open_video
    backend, reader, fps, total = _open_video(session.video_path)
    session.duration_sec = total / fps if fps else 0.0

    kf = json.loads(make_extract_keyframes(session).invoke(
        {"strategy": "uniform", "count": 8}))
    paths = [f.path for fid in kf["frame_ids"]
             if (f := session.cached_frames.get(fid)) and f.path]
    if paths:
        try:
            session.global_summary = get_vl_client().call_multi(
                paths,
                f"These {len(paths)} frames are uniformly sampled from a "
                f"{session.duration_sec:.0f}-second video. Write a 3-5 sentence "
                f"summary of what the video is about: setting, people, main "
                f"activities and their rough order. Mention any prominent "
                f"on-screen text. Factual only.",
                json_mode=False,
            ).strip()
        except Exception as exc:
            if verbose:
                print(f"  [L0] summary failed ({exc}); continuing without summary")
            session.global_summary = ""

    session.transcript = asr.transcribe(session.video_path)
    if verbose:
        print(f"  [L0] summary={'ok' if session.global_summary else 'EMPTY'}, "
              f"asr={len(session.transcript)} lines (local)")


def build_l0_context(session: "VideoSession") -> str:
    """Render the L0 layer (summary + transcript + explored windows) as the
    context prefix for a v2 agent invocation."""
    from src.perception.asr import transcript_text

    dur = getattr(session, "duration_sec", 0.0)
    lines = [f"[Video] duration ≈ {dur:.0f}s"]
    if session.global_summary:
        lines.append(f"[Global summary] {session.global_summary}")
    tr = transcript_text(getattr(session, "transcript", []))
    lines.append(f"[Narration transcript]\n{tr}" if tr
                 else "[Narration transcript] (none / no speech)")
    wins = session.explored_windows()
    if wins:
        lines.append("[Explored windows] "
                     + ", ".join(f"{a:.0f}-{b:.0f}s" for a, b in wins))
    return "\n".join(lines) + "\n\n"


def build_agent_v2(session: "VideoSession", short_answer: bool = True,
                   explore: bool = True) -> Any:
    """Create the v2 agent: lazy memory toolset + confidence-driven prompt.

    explore=True  : full toolset (search_memory + explore_segment + inspect_frame),
                    confidence-driven loop.
    explore=False : routing experiment — answer from L0 + a free memory search
                    only (no window zooming). Used for structural/reasoning
                    categories where exploration empirically hurts.

    Invoke with build_l0_context(session) + question as the user message.
    """
    from src.config import get_settings
    from src.tools.memory_search import make_search_memory
    from src.tools.segment_inspector import make_explore_segment

    if explore:
        tools = [
            make_search_memory(session),
            make_explore_segment(session),
            make_inspect_frame(session),
        ]
        core = _V2_SYSTEM_CORE
    else:
        tools = [make_search_memory(session)]
        core = _V2_SYSTEM_NOEXPLORE

    prompt = core + (_V2_ANSWER_SHORT if short_answer else _V2_ANSWER_VERBOSE)
    agent = create_agent(_get_real_llm(), tools, system_prompt=prompt, debug=False)
    agent._va_max_iterations = get_settings().agent.max_iterations  # type: ignore[attr-defined]
    return agent


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _get_real_llm():
    """ChatOpenAI pointing to the active LLM endpoint (DashScope or vLLM)."""
    from src.perception.vl_client import get_llm_client
    return get_llm_client()


# The mock deliberately makes NO claim about the video. It must stay visually
# distinct from a real answer (the [MOCK] prefix) and must never emit anything
# that looks like evidence — no scene-graph triplets, timestamps, or entities.
# See tests/test_agent.py::test_mock_answer_is_labeled_and_fabrication_free.
_MOCK_ANSWER = (
    "[MOCK] Offline smoke run — the agent loop and all tools executed "
    "end-to-end. This is a placeholder answer; it makes no claims about "
    "the actual video content. See the reasoning trace for real tool output."
)


class _ScriptedToolCallingModel(GenericFakeChatModel):
    """Fake chat model that replays a fixed script of AIMessages.

    GenericFakeChatModel.bind_tools raises NotImplementedError; we override it
    to return self so the scripted tool_calls flow through LangGraph unchanged
    and get routed to the real tool nodes.
    """

    def bind_tools(self, tools: list, **kwargs: Any) -> "_ScriptedToolCallingModel":  # type: ignore[override]
        return self


def _get_mock_llm() -> BaseChatModel:
    """
    Scripted offline LLM for smoke tests / no-API-key runs.

    Unlike a canned final answer, this genuinely exercises the agent loop: it
    emits two real tool calls (extract_keyframes -> query_scene_graph) that
    LangGraph routes to the actual tools, then returns the [MOCK] placeholder.
    Wrapped in itertools.cycle so interactive multi-turn sessions can replay
    the script across turns without exhausting the iterator.
    """
    script = [
        AIMessage(content="", tool_calls=[{
            "name": "extract_keyframes",
            "args": {"strategy": "uniform", "count": 4},
            "id": "mock_call_1", "type": "tool_call"}]),
        AIMessage(content="", tool_calls=[{
            "name": "query_scene_graph",
            "args": {"question": "What entities and relations are present?"},
            "id": "mock_call_2", "type": "tool_call"}]),
        AIMessage(content=_MOCK_ANSWER),
    ]
    return _ScriptedToolCallingModel(messages=cycle(script))
