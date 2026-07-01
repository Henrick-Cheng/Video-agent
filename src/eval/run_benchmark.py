"""
run_benchmark.py — Chinese Video QA benchmark runner.

Three methods compared:
  agent       : Full ReAct Agent (scene graph + tools)
  rag_only    : Build full scene graph once, LLM answers from graph text
  vlm_direct  : Send raw sampled frames + question directly to VLM

LLM-as-Judge: qwen-plus scores each answer 0 / 0.5 / 1 against key_facts.
Each method runs n_runs times; mean ± std reported.

Usage:
    python -m src.eval.run_benchmark \\
        --video data/videos/test1.mp4 \\
        --benchmark benchmarks/cn_video_qa_v1.json \\
        --runs 3 \\
        --methods agent,rag_only,vlm_direct \\
        --output docs/benchmark_results.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Force line-buffered stdout so progress prints appear immediately in background runs
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Judge prompt ──────────────────────────────────────────────────────────────

_JUDGE_PROMPT = """\
You are a strict video question-answering evaluator. Judge the quality of the candidate answer.

[Scoring]
- 1.0: the candidate contains all key facts and is semantically correct
- 0.5: the candidate contains more than half of the key facts; broadly correct but with omissions
- 0.0: the candidate is wrong, irrelevant, or hits less than 50% of the key facts

[Notes]
- Numbers must be exact ("2" vs "3" scores 0)
- Semantically equivalent words are acceptable ("hall" ≈ "lobby")
- Output only one number: 0, 0.5, or 1 — no explanation

Question: {question}
Reference answer: {reference}
Key facts (must be hit): {key_facts}
Candidate answer: {candidate}

Score (output only 0, 0.5, or 1): """


# ── Short-answer constraint (AGQA exact-match protocol) ───────────────────────
# AGQA gold answers are short canonical tokens (mostly yes/no, plus short object/
# action phrases). The postdoc's requirement: constrain every method via a system
# prompt to emit ONLY the short answer, so strict exact-match is meaningful.
_SHORT_ANSWER_SYS = (
    "You are answering questions about a video. Reply with ONLY the answer itself "
    "— a single word or a short phrase. For yes/no questions, answer exactly "
    "'yes' or 'no'. Do NOT add any explanation, reasoning, punctuation, or extra "
    "words."
)


# ── Token tracker ─────────────────────────────────────────────────────────────

class _TrialStats:
    """Real measured token usage for one unit of work (a question, or a prebuild).

    Every number comes from API-reported ``usage`` — the old per-method
    estimates (chars/3 for agent, frames*1500 for vlm_direct) mixed measurement
    methodologies across methods and carried a language bias (Phase 12
    finding #3). Text-LLM and VL-model tokens are bucketed separately: they are
    priced differently, and VL prompt tokens are dominated by image tokens.
    """

    def __init__(self):
        self.llm_prompt = 0
        self.llm_completion = 0
        self.vl_prompt = 0
        self.vl_completion = 0
        self.api_calls = 0
        self.frames = 0  # images sent to VL calls (frames-touched metric)

    def add_llm_usage(self, usage):
        """One text-LLM response's usage (OpenAI SDK object)."""
        if usage is None:
            return
        self.llm_prompt += getattr(usage, "prompt_tokens", 0) or 0
        self.llm_completion += getattr(usage, "completion_tokens", 0) or 0
        self.api_calls += 1

    def add_usage_metadata(self, um):
        """One LangChain AIMessage.usage_metadata dict (agent model turns).

        Each ReAct turn re-sends the full history, and input_tokens reflects
        that — summing over turns gives the true cumulative billing, which the
        old final-transcript estimate structurally undercounted.
        """
        if not um:
            return
        self.llm_prompt += um.get("input_tokens", 0)
        self.llm_completion += um.get("output_tokens", 0)
        self.api_calls += 1

    def add_vl_delta(self, delta: dict):
        """A LEDGER.since() delta covering this unit's VLClient calls."""
        self.vl_prompt += delta["prompt_tokens"]
        self.vl_completion += delta["completion_tokens"]
        self.api_calls += delta["calls"]
        self.frames += delta.get("images", 0)

    @property
    def llm_tokens(self):
        return self.llm_prompt + self.llm_completion

    @property
    def vl_tokens(self):
        return self.vl_prompt + self.vl_completion

    @property
    def total_tokens(self):
        return self.llm_tokens + self.vl_tokens


# ── Method implementations ────────────────────────────────────────────────────

def _build_session(video_path: str):
    from src.memory.session import VideoSession
    return VideoSession(video_path=video_path)


def _prebuild_graph(session, frame_count: int = 8) -> _TrialStats:
    """Extract frames and build full scene graph. Returns real token stats
    (the build's VL calls — including ThreadPoolExecutor workers — all land in
    the global LEDGER via VLClient)."""
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph
    from src.perception.usage import LEDGER

    stats = _TrialStats()
    marker = LEDGER.marker()

    kf_tool = make_extract_keyframes(session)
    sg_tool = make_build_scene_graph(session)

    result = json.loads(kf_tool.invoke({"strategy": "uniform", "count": frame_count}))
    frame_ids = ",".join(result["frame_ids"])
    sg_tool.invoke({"frame_ids": frame_ids, "focus_entities": ""})

    stats.add_vl_delta(LEDGER.since(marker))
    return stats


def _prepare_l0(session) -> _TrialStats:
    """v2 per-video init: sparse-frame global summary (1 VL call) + local ASR.

    This replaces the v1 full-graph prebuild — the only upfront costs are one
    cheap summary call and a zero-token local transcription; everything else
    is built on demand by the agent."""
    from src.perception.usage import LEDGER
    from src.perception.vl_client import get_vl_client
    from src.perception import asr
    from src.tools.keyframe import make_extract_keyframes

    stats = _TrialStats()
    marker = LEDGER.marker()

    session.duration_sec = _video_duration_sec(session.video_path)

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
            # A summary failure must not crash a multi-hour run — degrade to
            # empty (the agent still has the transcript + exploration).
            print(f"  [L0] summary failed ({exc}); continuing without summary")
            session.global_summary = ""

    t0 = time.time()
    session.transcript = asr.transcribe(session.video_path)
    asr_sec = time.time() - t0
    print(f"  [L0] summary={'ok' if session.global_summary else 'EMPTY'}, "
          f"asr={len(session.transcript)} lines ({asr_sec:.0f}s local)")

    stats.add_vl_delta(LEDGER.since(marker))
    return stats


# qwen-plus occasionally emits a tool call as plain text (no tool_calls field)
# and the run ends with e.g. `search_memory("...")` as the "answer". Detect and
# retry once with a corrective instruction. The detector is shared with the
# product CLI — see react_agent.looks_like_pseudo_call.


def _answer_agent_v2(session, question: str,
                     short_answer: bool = True,
                     allow_explore: bool = True) -> tuple[str, int, _TrialStats]:
    """v2: lazy memory + confidence-driven loop (see react_agent.build_agent_v2).

    allow_explore=False routes the question to the no-explore variant (answer
    from L0 + free memory search only) — the structural-category routing
    experiment.
    """
    from src.agents.react_agent import (
        build_agent_v2, build_l0_context, looks_like_pseudo_call)

    agent = build_agent_v2(session, short_answer=short_answer, explore=allow_explore)
    rl = getattr(agent, "_va_max_iterations", 6) * 5 + 10
    user_text = build_l0_context(session) + question

    answer, tool_calls, stats = _invoke_and_account(agent, user_text, rl)

    if looks_like_pseudo_call(answer):
        print("         [retry] final message was a textual pseudo-call — re-asking")
        corrective = (
            f"{user_text}\n\nYour previous reply was plain text that LOOKED like "
            f"a tool call ({answer[:80]}); it was not executed. Either CALL the "
            f"tool through the tool-calling interface, or give your final answer."
        )
        answer2, tc2, stats2 = _invoke_and_account(agent, corrective, rl)
        # Merge accounting: both attempts were really billed.
        stats.llm_prompt += stats2.llm_prompt
        stats.llm_completion += stats2.llm_completion
        stats.vl_prompt += stats2.vl_prompt
        stats.vl_completion += stats2.vl_completion
        stats.api_calls += stats2.api_calls
        answer, tool_calls = answer2, tool_calls + tc2

    return answer, tool_calls, stats


# Benchmark-only agent system prompt: keep the tool-use strategy, but require a
# SHORT final answer (the product default cites evidence, which is verbose and
# defeats exact-match). This is a system message so it overrides the user turn.
_AGENT_EVAL_SYSTEM = """\
You are a video question-answering assistant with a pre-built temporal scene graph \
as structured memory (triplets: (subject) --[relation]--> (object) @ [t_start, t_end]).

[Decision strategy]
1. You MUST call query_scene_graph to retrieve relevant facts before answering.
2. If the graph is insufficient, call inspect_frame for a specific timestamp.
3. The scene graph and frames are already built — do NOT call extract_keyframes or \
build_scene_graph.
4. Never answer from prior knowledge or guess; ground every answer in the retrieved \
evidence.

[Answer format — strict]
Your FINAL message must be ONLY the answer itself: a single word or a short phrase. \
For yes/no questions, answer exactly 'yes' or 'no'. Do NOT include any explanation, \
reasoning, triplets, timestamps, or extra words in the final message."""


def _answer_agent(session, question: str,
                  short_answer: bool = True) -> tuple[str, int, _TrialStats]:
    """Answer using full ReAct agent (scene graph already pre-built).

    short_answer=True  → terse final answer (exact-match setup).
    short_answer=False → product default system prompt (verbose, cites evidence);
                         used for the LLM-judge comparison against the old runs.
    """
    from src.agents.react_agent import build_agent

    # short → benchmark short-answer system prompt; verbose → product default (None)
    agent = build_agent(session,
                        system_prompt=_AGENT_EVAL_SYSTEM if short_answer else None)
    rl = getattr(agent, "_va_max_iterations", 6) * 5 + 10

    # Inject graph status so agent skips rebuild and goes directly to query/inspect
    n_e = len(session.scene_graph.entities)
    n_t = len(session.scene_graph)
    n_f = len(session.cached_frames)
    if short_answer:
        ctx_prefix = (
            f"[The scene graph is pre-built: {n_e} entities, {n_t} triplets, "
            f"{n_f} frames cached.]\n\n"
        )
    else:
        # Verbose mode: the product system prompt lacks the prebuilt-graph hint,
        # so spell out the anti-rebuild guidance here (matches the pre-change run).
        ctx_prefix = (
            f"[The scene graph is pre-built: {n_e} entities, {n_t} triplets, "
            f"{n_f} frames cached. Use query_scene_graph to retrieve directly, and "
            f"inspect_frame when you need more detail. Do NOT call extract_keyframes "
            f"or build_scene_graph again.]\n\n"
        )

    return _invoke_and_account(agent, ctx_prefix + question, rl)


def _invoke_and_account(agent, user_text: str, rl: int) -> tuple[str, int, _TrialStats]:
    """Invoke a compiled agent and collect real token usage.

    Agent-model turns: each AIMessage carries the API-reported usage for its
    call (input side = full re-sent history, so the sum is true billing).
    Tool-side VL calls (inspect_frame) are captured via the global ledger.
    """
    from src.perception.usage import LEDGER
    marker = LEDGER.marker()

    try:
        result = agent.invoke(
            {"messages": [("user", user_text)]},
            config={"recursion_limit": rl},
        )
        msgs = result.get("messages", [])
    except Exception as exc:
        # GraphRecursionError or other agent failure — score as empty answer
        print(f"         [WARN] agent.invoke failed: {exc}")
        msgs = []

    answer = msgs[-1].content if msgs else ""
    tool_calls = sum(1 for m in msgs if getattr(m, "type", "") == "tool")

    stats = _TrialStats()
    for m in msgs:
        stats.add_usage_metadata(getattr(m, "usage_metadata", None))
    stats.add_vl_delta(LEDGER.since(marker))

    if msgs and stats.llm_tokens == 0:
        print("         [WARN] no usage_metadata on agent messages — "
              "LLM endpoint did not report usage; agent tokens undercounted")

    return answer, tool_calls, stats


# ── Tiered agent ──────────────────────────────────────────────────────────────
# Cost-aware variant: the scene graph (or its summary, when large) is injected
# directly into the user context, and the model DECIDES AT RUNTIME whether that
# suffices or whether to escalate to tools. Easy questions thus cost one LLM
# call (~rag_only floor); hard ones pay for retrieval/inspection. The
# escalation is the model's own choice, not a hardcoded router.

# Graphs at or below this size are injected verbatim; larger graphs get an
# entity summary and the agent must retrieve via query_scene_graph.
_TIERED_GRAPH_FULL_THRESHOLD = 30

_TIERED_SYSTEM_SHORT = """\
You are a video question-answering assistant. The video's temporal scene graph \
(triplets: (subject) --[relation]--> (object) @ [t_start, t_end]) is provided in \
the user message.

[Decision strategy]
1. If the provided scene graph already contains the facts needed, answer \
DIRECTLY without calling any tool — every tool call costs money and time.
2. If the provided context is only a summary, or lacks the needed facts, call \
query_scene_graph to retrieve more specific triplets.
3. Only when the graph cannot answer (reading text, exact counting, \
fine-grained visual attributes) call inspect_frame at a specific timestamp.
4. The graph and frames are pre-built — never call extract_keyframes or \
build_scene_graph.
5. Never answer from prior knowledge; ground every answer in the graph or \
inspected frames.
6. IMPORTANT: the graph is built from sparse frames and may miss events. \
Absence of a fact in the graph is NOT evidence of 'no'. If the graph does not \
explicitly contain the fact needed, verify with inspect_frame BEFORE answering \
— especially for yes/no questions.

[Answer format — strict]
Your FINAL message must be ONLY the answer itself: a single word or a short \
phrase. For yes/no questions, answer exactly 'yes' or 'no'. Do NOT include any \
explanation, reasoning, triplets, timestamps, or extra words in the final message."""

_TIERED_SYSTEM_VERBOSE = """\
You are a video question-answering assistant. The video's temporal scene graph \
(triplets: (subject) --[relation]--> (object) @ [t_start, t_end]) is provided in \
the user message.

[Decision strategy]
1. If the provided scene graph already contains the facts needed, answer \
DIRECTLY without calling any tool — every tool call costs money and time.
2. If the provided context is only a summary, or lacks the needed facts, call \
query_scene_graph to retrieve more specific triplets.
3. Only when the graph cannot answer (reading text, exact counting, \
fine-grained visual attributes) call inspect_frame at a specific timestamp.
4. The graph and frames are pre-built — never call extract_keyframes or \
build_scene_graph.
5. Never answer from prior knowledge; ground every answer in the graph or \
inspected frames.
6. IMPORTANT: the graph is built from sparse frames and may miss events. \
Absence of a fact in the graph is NOT evidence of 'no'. If the graph does not \
explicitly contain the fact needed, verify with inspect_frame BEFORE answering \
— especially for yes/no questions.

[Answer format]
Give a concise, accurate answer (1-3 sentences). Mention timestamps when they \
are relevant to the question."""


def _tiered_context(session) -> str:
    """Graph context injected ahead of the question for the tiered agent."""
    g = session.scene_graph
    if len(g) <= _TIERED_GRAPH_FULL_THRESHOLD:
        return f"[Pre-built scene graph]\n{g.to_text(max_triplets=_TIERED_GRAPH_FULL_THRESHOLD)}\n\n"
    entities = ", ".join(list(g.entities.keys())[:40])
    return (
        f"[Pre-built scene graph: {len(g.entities)} entities, {len(g)} triplets — "
        f"too large to inline; use query_scene_graph to retrieve relevant facts.]\n"
        f"[Known entities: {entities}]\n\n"
    )


def _answer_agent_tiered(session, question: str,
                         short_answer: bool = True) -> tuple[str, int, _TrialStats]:
    """Tiered agent: graph injected into context, tools optional, model decides."""
    from src.agents.react_agent import build_agent

    sys_prompt = _TIERED_SYSTEM_SHORT if short_answer else _TIERED_SYSTEM_VERBOSE
    agent = build_agent(session, system_prompt=sys_prompt)
    rl = getattr(agent, "_va_max_iterations", 6) * 5 + 10

    return _invoke_and_account(agent, _tiered_context(session) + question, rl)


def _answer_rag_only(session, question: str,
                     short_answer: bool = True) -> tuple[str, int, _TrialStats]:
    """LLM answers from scene graph text only."""
    from openai import OpenAI
    from src.config import get_settings
    from src.perception.vl_client import get_llm_client

    cfg = get_settings()
    graph_text = session.scene_graph.to_text()

    llm = get_llm_client()
    stats = _TrialStats()

    if short_answer:
        prompt = (
            f"Answer the question based ONLY on the following scene graph information; "
            f"do not go beyond it.\n\n{graph_text}\n\nQuestion: {question}"
        )
        messages = [
            {"role": "system", "content": _SHORT_ANSWER_SYS},
            {"role": "user", "content": prompt},
        ]
        max_toks = 64
    else:
        prompt = (
            f"You are a video content analysis assistant. Answer the question based on "
            f"the following scene graph information; do not go beyond it.\n\n"
            f"{graph_text}\n\nQuestion: {question}\n\n"
            f"Give a concise, accurate answer (2-4 sentences): "
        )
        messages = [{"role": "user", "content": prompt}]
        max_toks = 512

    try:
        resp = OpenAI(
            base_url=cfg.active_llm.base_url,
            api_key=cfg.dashscope_api_key or "token-abc",
        ).chat.completions.create(
            model=cfg.active_llm.model_name,
            messages=messages,
            max_tokens=max_toks,
            temperature=cfg.models.llm.temperature,
        )
        stats.add_llm_usage(resp.usage)
        answer = resp.choices[0].message.content or ""
    except Exception as e:
        answer = f"[ERROR] {e}"

    return answer, 0, stats


# Number of frames vlm_direct sends to the VLM. Fixed and deliberately
# independent of perception.keyframe_count: this baseline must NOT inherit the
# agent's prebuild frame count, or a config change meant for the agent silently
# alters the baseline's inputs and invalidates cross-run comparisons.
_VLM_DIRECT_FRAME_COUNT = 4
# Oversample factor for vlm_direct extraction. We extract more uniform frames
# than needed, then pick _VLM_DIRECT_FRAME_COUNT evenly-spaced *valid* ones.
# This guards against the OpenCV last-frame read failure (cv2 routinely reports
# more frames than it can decode), which would otherwise silently drop the
# final frame and front-load the sample — missing the end of the video.
_VLM_DIRECT_OVERSAMPLE = 8


def _answer_vlm_direct(session, question: str,
                       short_answer: bool = True,
                       frame_count: int | None = None,
                       with_transcript: bool = False) -> tuple[str, int, _TrialStats]:
    """Send sampled frames + question directly to VLM.

    Extracts its own uniform frames at a fixed count rather than reusing the
    pre-built scene-graph frames in session.cached_frames — otherwise
    perception.keyframe_count leaks into this baseline (e.g. 8→16 changed which
    4 frames it saw), making Phase-to-Phase comparisons invalid.

    Oversamples then sub-selects so the 4 frames reliably span the whole video
    even when OpenCV fails to decode the final frame index.
    """
    import numpy as np
    from src.perception.vl_client import get_vl_client
    from src.tools.keyframe import make_extract_keyframes
    from src.config import get_settings

    cfg = get_settings()
    stats = _TrialStats()
    n_frames = frame_count or _VLM_DIRECT_FRAME_COUNT
    oversample = max(2 * n_frames, _VLM_DIRECT_OVERSAMPLE)

    # Independent uniform extraction — decoupled from the prebuilt graph.
    kf_tool = make_extract_keyframes(session)
    try:
        kf_result = json.loads(kf_tool.invoke(
            {"strategy": "uniform", "count": oversample}
        ))
        frame_ids = kf_result["frame_ids"]
    except Exception as e:
        return f"[ERROR] keyframe extraction failed: {e}", 0, stats

    valid = [
        fm for fid in frame_ids
        if (fm := session.cached_frames.get(fid))
        and fm.path and Path(fm.path).exists()
    ]

    if not valid:
        return "[ERROR] no valid frame files", 0, stats

    # Pick n_frames evenly-spaced frames spanning the full video.
    valid.sort(key=lambda f: f.timestamp)
    if len(valid) > n_frames:
        picks = np.linspace(0, len(valid) - 1, n_frames, dtype=int)
        selected = [valid[i] for i in dict.fromkeys(int(p) for p in picks)]
    else:
        selected = valid

    from src.perception.usage import LEDGER

    # Fairness baseline (vlm_transcript): same frames, plus the narration
    # transcript in the prompt — isolates "extra modality" from "architecture".
    transcript_block = ""
    if with_transcript:
        from src.perception.asr import transcript_text
        tr = transcript_text(getattr(session, "transcript", []))
        transcript_block = (
            f"Narration transcript of the video:\n{tr}\n\n" if tr
            else "Narration transcript of the video: (no speech)\n\n"
        )

    vl = get_vl_client()
    marker = LEDGER.marker()
    try:
        if short_answer:
            prompt = (f"{transcript_block}Answer the question based on these "
                      f"video frames: {question}")
            answer = vl.call_multi([f.path for f in selected], prompt,
                                   system_prompt=_SHORT_ANSWER_SYS, json_mode=False)
        else:
            prompt = (
                f"{transcript_block}Answer the question based on these video "
                f"frames: {question}\n\n"
                f"Give a concise, accurate answer (2-4 sentences)."
            )
            answer = vl.call_multi([f.path for f in selected], prompt)
    except Exception as e:
        answer = f"[ERROR] {e}"

    # Real usage from the VL call (image tokens included in prompt_tokens) —
    # replaces the old frames*1500 estimate.
    stats.add_vl_delta(LEDGER.since(marker))

    return answer, 0, stats


# ── Judges ────────────────────────────────────────────────────────────────────

# Default scorers (AGQA protocol). Each question is scored once per active
# scorer; results are reported side-by-side (one column each).
SCORERS = ("llm", "exact")
# All scorers the runner knows about. "mmbv" replicates the official
# MMBench-Video protocol and is opted into via --scorers mmbv.
ALL_SCORERS = ("llm", "exact", "mmbv")


def _judge_client():
    """
    OpenAI-compatible client for the LLM judge.

    The judge endpoint is configurable INDEPENDENTLY of the agent/VL models via
    env vars, so the paper-grade judge can be swapped to GPT (academic norm —
    avoids a Qwen-judging-Qwen self-preference confound) without touching the
    pipeline. Falls back to the active DashScope LLM.
    """
    from openai import OpenAI
    from src.config import get_settings

    cfg = get_settings()
    base = os.environ.get("JUDGE_BASE_URL", cfg.active_llm.base_url)
    key = os.environ.get("JUDGE_API_KEY") or cfg.dashscope_api_key or "token-abc"
    return OpenAI(base_url=base, api_key=key, max_retries=6, timeout=60.0)


def _judge_model() -> str:
    from src.config import get_settings
    return os.environ.get("JUDGE_MODEL", get_settings().active_llm.model_name)


def _judge_llm(question: str, reference: str, key_facts: list[str],
               candidate: str) -> float:
    """LLM-as-Judge: returns 0, 0.5, or 1 (partial credit)."""
    prompt = _JUDGE_PROMPT.format(
        question=question,
        reference=reference,
        key_facts=", ".join(key_facts),
        candidate=candidate,
    )

    try:
        resp = _judge_client().chat.completions.create(
            model=_judge_model(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16,
            temperature=0.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if "1" in raw and "0" not in raw.replace("1", ""):
            return 1.0
        if "0.5" in raw:
            return 0.5
        return 0.0
    except Exception:
        return 0.0


# ── MMBench-Video official judge (VLMEvalKit protocol) ────────────────────────
# Replicated VERBATIM from open-compass/VLMEvalKit
# vlmeval/dataset/utils/mmbench_video.py (the protocol used by the official
# OpenVLM Video Leaderboard and papers reporting on MMBench-Video).
# Official judge model is gpt-4-turbo; we run the identical prompt through the
# configurable judge endpoint (JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY) —
# DashScope for test runs, OpenAI for paper numbers — and disclose the model.

_MMBV_SYSTEM_PROMPT = """
As an AI assistant, your task is to evaluate a candidate answer in comparison to a given correct answer.
The question itself, the correct 'groundtruth' answer, and the candidate answer will be provided to you.
Your assessment should range from 0 to 3, \
based solely on the semantic similarity between the groundtruth and the candidate answer, \
disregarding any grammatical differences.
A rating of 0 suggests no similarity, implying the candidate answer is entirely incorrect.
A rating of 1 suggests low similarity, meaning the candidate answer is largely incorrect.
A rating of 2 suggests high similarity, meaning the candidate answer is largely correct.
Lastly, a rating of 3 indicates complete similarity, which means the candidate answer is entirely correct.
Your response should be a single integer from 0, 1, 2, or 3.
"""

_MMBV_USER_TMPL = (
    "Question: {}\nGroundtruth answer: {}\nCandidate answer: {}\nYour response: "
)


def _judge_mmbv(question: str, reference: str, candidate: str) -> float:
    """Official MMBench-Video 0-3 semantic-similarity score.

    Returns -1.0 when the judge call or integer parse fails (the official
    FAIL convention); aggregation maps -1 → 0 ('all' variant), and the raw
    -1 stays in the result JSON for auditability.
    """
    for _attempt in range(2):
        try:
            resp = _judge_client().chat.completions.create(
                model=_judge_model(),
                messages=[
                    {"role": "system", "content": _MMBV_SYSTEM_PROMPT},
                    {"role": "user", "content": _MMBV_USER_TMPL.format(
                        question, reference, candidate)},
                ],
                max_tokens=8,
                temperature=0.0,
            )
            raw = (resp.choices[0].message.content or "").strip()
            m = re.search(r"[0-3]", raw)
            if m:
                return float(m.group(0))
        except Exception:
            continue
    print("         [WARN] mmbv judge failed — recording -1")
    return -1.0


# ── Exact-match judge (AGQA paper protocol) ───────────────────────────────────

_ARTICLES_RE = re.compile(r"\b(a|an|the)\b")
_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")
_YESNO_RE = re.compile(r"\b(yes|no)\b")


def _normalize_answer(s: str) -> str:
    """Lowercase, strip punctuation/articles, collapse whitespace."""
    s = _PUNCT_RE.sub(" ", s.lower())
    s = _ARTICLES_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def _judge_exact(candidate: str, gold: str, category: str = "") -> float:
    """
    Exact-match score (1.0 / 0.0), AGQA-style, adapted for free-form output.

    - binary  : compare the first yes/no mentioned in the candidate to the gold.
    - other   : relaxed containment EM — 1.0 if the normalized gold appears as a
                contiguous substring or a full token-subset of the normalized
                candidate (the agent answers in sentences, gold is a short token).

    Note: this is "relaxed containment EM", not token-identical EM, because the
    pipeline produces sentences rather than AGQA's canonical short answers.
    Documented as such in the report.
    """
    g = _normalize_answer(gold)
    a = _normalize_answer(candidate)
    if not g:
        return 0.0

    if category == "binary" or g in ("yes", "no"):
        m = _YESNO_RE.search(a)
        pred = m.group(1) if m else ""
        return 1.0 if pred == g else 0.0

    # Strict exact match on short answers. Methods are constrained (via
    # _SHORT_ANSWER_SYS) to emit only the answer, so normalized equality is the
    # right test. A small length-guarded containment tolerates trivial wrappers
    # ("the bed" → "bed") WITHOUT re-admitting the long-answer false positives
    # (a verbose reasoning dump that merely mentions the gold word in passing).
    if a == g:
        return 1.0
    if len(a.split()) <= len(g.split()) + 2 and g in a:
        return 1.0
    return 0.0


# ── Short-answer extraction (fairness for exact-match) ────────────────────────
# Single-shot baselines obey the short-answer system prompt, but the multi-turn
# ReAct agent narrates its final turn regardless. To compare exact-match FAIRLY
# (correctness, not verbosity), reduce any verbose answer to its canonical short
# form before EM. The LLM judge still scores the raw answer.
_EXTRACT_PROMPT = """\
Extract the final answer from the response below. Output ONLY the answer as a \
single word or short phrase (for yes/no questions, exactly 'yes' or 'no'). \
Do not explain.

Question: {question}
Response: {response}

Final short answer:"""


def _extract_short_answer(raw: str, question: str) -> str:
    """Reduce a (possibly verbose) answer to its canonical short form."""
    from openai import OpenAI
    from src.config import get_settings

    if not raw or not raw.strip():
        return ""
    # Already short → no extraction needed (and no extra API cost).
    if len(raw.split()) <= 6:
        return raw.strip()

    cfg = get_settings()
    try:
        resp = OpenAI(
            base_url=cfg.active_llm.base_url,
            api_key=cfg.dashscope_api_key or "token-abc",
        ).chat.completions.create(
            model=cfg.active_llm.model_name,
            messages=[{"role": "user", "content":
                       _EXTRACT_PROMPT.format(question=question, response=raw)}],
            max_tokens=32,
            temperature=0.0,
        )
        return (resp.choices[0].message.content or "").strip() or raw.strip()
    except Exception:
        return raw.strip()


def _score_answer(scorer: str, qa: dict, candidate: str) -> float:
    """Dispatch one scorer over one (question, candidate) pair."""
    if scorer == "llm":
        return _judge_llm(qa["question"], qa["reference_answer"],
                          qa["key_facts"], candidate)
    if scorer == "exact":
        gold = (qa.get("_source") or {}).get("en_answer") or qa["reference_answer"]
        return _judge_exact(candidate, gold, qa.get("category", ""))
    if scorer == "mmbv":
        return _judge_mmbv(qa["question"], qa["reference_answer"], candidate)
    raise ValueError(f"Unknown scorer: {scorer}")


# ── Trial runner ──────────────────────────────────────────────────────────────

def _video_duration_sec(path: str) -> float:
    import cv2
    cap = cv2.VideoCapture(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        return n / fps if fps > 0 else 0.0
    finally:
        cap.release()


def _prebuild_frame_count(duration_sec: float, default: int) -> int:
    """Duration-adaptive prebuild frame budget: one frame per ~15s, clamped to
    [8, 24]. Keeps Charades-length clips (30-40s) at the historical 8 frames
    (comparable with earlier runs) while giving minutes-long videos fair
    scene-graph coverage."""
    if duration_sec <= 0:
        return default
    return min(24, max(8, int(duration_sec / 15)))


def run_trial(
    method: str,
    video_path: Optional[str],
    questions: list[dict],
    scorers: tuple[str, ...] = SCORERS,
    short_answer: bool = True,
    vlm_frames: Optional[int] = None,
    skip_explore_categories: frozenset = frozenset(),
) -> list[dict]:
    """Run all questions for one method in one trial. Returns per-question results.

    Questions are grouped by their per-question ``video`` field (falling back to
    ``video_path`` when a question omits it). For each video we build one
    VideoSession and — for methods that read the scene graph (agent / rag_only) —
    pre-build the graph once and reuse it across that video's questions.
    vlm_direct extracts its own frames per question, so it skips the prebuild.

    Each answer is scored once per active scorer in ``scorers`` (e.g. both the
    LLM judge and exact-match), stored under ``scores[scorer]``.
    """
    from src.config import get_settings as _get_settings

    # Group questions by video, preserving first-seen order.
    groups: dict[str, list[dict]] = {}
    for qa in questions:
        v = qa.get("video") or video_path
        if not v:
            raise ValueError(
                f"question {qa.get('id')!r} has no 'video' field and no --video fallback"
            )
        groups.setdefault(v, []).append(qa)

    needs_graph = method in ("agent", "agent_tiered", "rag_only")
    needs_l0 = method == "agent_v2"
    needs_transcript = method == "vlm_transcript"
    results: list[dict] = []

    for v, qas in groups.items():
        if not Path(v).exists():
            print(f"  [skip] video file not found — skipping {len(qas)} question(s): {v}")
            continue

        session = _build_session(v)
        prebuild_share = 0.0
        if needs_graph:
            n_pb = _prebuild_frame_count(
                _video_duration_sec(v), _get_settings().perception.keyframe_count)
            print(f"  [prebuild] {Path(v).name}: extracting {n_pb} frames "
                  f"& building graph...")
            pb = _prebuild_graph(session, frame_count=n_pb)
            # One-time build cost amortized over this video's benchmark questions
            # (production analogue: conversation length per video).
            prebuild_share = pb.total_tokens / len(qas)
            print(f"  [prebuild] graph: {len(session.scene_graph.entities)} entities, "
                  f"{len(session.scene_graph)} triplets, "
                  f"{pb.total_tokens} tokens ({pb.api_calls} VL calls) "
                  f"→ {prebuild_share:.0f}/Q amortized over {len(qas)} Qs")
        elif needs_l0:
            print(f"  [L0-init] {Path(v).name}: summary + transcript...")
            pb = _prepare_l0(session)
            prebuild_share = pb.total_tokens / len(qas)
            print(f"  [L0-init] {pb.total_tokens} tokens "
                  f"→ {prebuild_share:.0f}/Q over {len(qas)} Qs")
        elif needs_transcript:
            from src.perception import asr
            session.transcript = asr.transcribe(v)
            print(f"  [asr] {Path(v).name}: {len(session.transcript)} lines (local)")

        for i, qa in enumerate(qas):
            q = qa["question"]
            print(f"  Q{i+1:02d} [{qa['category']}] {q[:40]}...")
            t0 = time.time()

            if method == "agent":
                answer, tool_calls, stats = _answer_agent(session, q, short_answer)
            elif method == "agent_v2":
                allow_explore = qa["category"] not in skip_explore_categories
                answer, tool_calls, stats = _answer_agent_v2(
                    session, q, short_answer, allow_explore=allow_explore)
            elif method == "agent_tiered":
                answer, tool_calls, stats = _answer_agent_tiered(session, q, short_answer)
            elif method == "rag_only":
                answer, tool_calls, stats = _answer_rag_only(session, q, short_answer)
            elif method == "vlm_direct":
                answer, tool_calls, stats = _answer_vlm_direct(
                    session, q, short_answer, frame_count=vlm_frames)
            elif method == "vlm_transcript":
                answer, tool_calls, stats = _answer_vlm_direct(
                    session, q, short_answer, frame_count=vlm_frames,
                    with_transcript=True)
            else:
                raise ValueError(f"Unknown method: {method}")

            elapsed = time.time() - t0
            # Exact-match scores the canonical short answer; the LLM judge scores
            # the raw answer (it tolerates verbosity). Extraction is a no-op for
            # already-short outputs.
            answer_short = (_extract_short_answer(answer, q)
                            if "exact" in scorers else answer)
            scores = {
                s: _score_answer(s, qa, answer_short if s == "exact" else answer)
                for s in scorers
            }
            score_str = " ".join(f"{s}={scores[s]}" for s in scorers)
            print(f"         {score_str} time={elapsed:.1f}s tools={tool_calls} "
                  f"tok={stats.total_tokens}")

            results.append({
                "id": qa["id"],
                "video": v,
                "category": qa["category"],
                "question": q,
                "answer": answer,
                "answer_short": answer_short,
                "scores": scores,
                "tool_calls": tool_calls,
                "time_sec": round(elapsed, 2),
                "tokens": stats.total_tokens,
                "tokens_llm": stats.llm_tokens,
                "tokens_vl": stats.vl_tokens,
                "frames_touched": stats.frames,
                "prebuild_share": round(prebuild_share, 1),
            })

    return results


# ── Statistics helpers ────────────────────────────────────────────────────────

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _score_of(r: dict, scorer: str) -> float:
    """Read one scorer's value from a result row (back-compat with old 'score')."""
    if "scores" in r:
        v = r["scores"].get(scorer, 0.0)
        # mmbv: judge failures are stored as -1; official 'all' aggregation
        # treats them as 0 (the raw -1 remains in the JSON for audit).
        return max(v, 0.0) if scorer == "mmbv" else v
    return r.get("score", 0.0)  # legacy single-score rows


def _aggregate_scorer(all_trials: list[list[dict]], scorer: str,
                      categories: list[str]) -> dict:
    """Aggregate overall + per-category mean/std for a single scorer."""
    overall_scores = [
        _mean([_score_of(r, scorer) for r in trial]) for trial in all_trials
    ]
    cat_scores: dict[str, list[float]] = {c: [] for c in categories}
    for trial in all_trials:
        by_cat: dict[str, list[float]] = {c: [] for c in categories}
        for r in trial:
            by_cat[r["category"]].append(_score_of(r, scorer))
        for c in categories:
            cat_scores[c].append(_mean(by_cat[c]) if by_cat[c] else 0.0)

    return {
        "overall_mean": round(_mean(overall_scores), 3),
        "overall_std":  round(_std(overall_scores), 3),
        "by_category": {
            c: {
                "mean": round(_mean(cat_scores[c]), 3),
                "std":  round(_std(cat_scores[c]), 3),
            }
            for c in categories
        },
    }


def _aggregate(all_trials: list[list[dict]],
               scorers: tuple[str, ...] = SCORERS) -> dict:
    """Aggregate multiple trial result lists into per-scorer mean/std stats."""
    categories = list(dict.fromkeys(r["category"] for trial in all_trials for r in trial))

    tool_calls_per_trial = [
        _mean([r["tool_calls"] for r in trial]) for trial in all_trials
    ]
    time_per_trial = [
        _mean([r["time_sec"] for r in trial]) for trial in all_trials
    ]
    tokens_per_q = [
        _mean([r["tokens"] for r in trial]) for trial in all_trials
    ]
    prebuild_per_q = [
        _mean([r.get("prebuild_share", 0.0) for r in trial]) for trial in all_trials
    ]
    frames_per_q = [
        _mean([r.get("frames_touched", 0) for r in trial]) for trial in all_trials
    ]

    return {
        "scorers": {s: _aggregate_scorer(all_trials, s, categories) for s in scorers},
        "avg_tool_calls": round(_mean(tool_calls_per_trial), 1),
        "avg_time_sec":   round(_mean(time_per_trial), 1),
        # Marginal answer-phase cost; prebuild share amortizes the one-time
        # scene-graph build over each video's questions (0 for vlm_direct).
        "avg_tokens_per_q":   int(_mean(tokens_per_q)),
        "avg_prebuild_per_q": int(_mean(prebuild_per_q)),
        "avg_total_tokens_per_q": int(_mean(tokens_per_q) + _mean(prebuild_per_q)),
        "avg_frames_per_q": round(_mean(frames_per_q), 1),
    }


# ── Report generation ─────────────────────────────────────────────────────────

_CAT_LABELS = {
    # AGQA categories
    "binary":     "binary",
    "duration":   "duration",
    "sequencing": "sequencing",
    "open":       "open",
    # cooking-set categories (legacy)
    "object":     "object recognition",
    "attribute":  "entity attribute",
    "relation":   "relation reasoning",
    "temporal":   "temporal reasoning",
    "count":      "counting / presence",
}


_SCORER_LABELS = {
    "llm":   "LLM-judge (0/0.5/1)",
    "exact": "exact-match",
    "mmbv":  "MMBench-Video official (0-3)",
}


def _per_video_lines(raw_by_method: dict[str, list[list[dict]]],
                     scorer: str) -> list[str]:
    """Markdown table of per-video accuracy (method × video). Empty if ≤1 video."""
    methods = list(raw_by_method.keys())
    videos: list[str] = []
    for trials in raw_by_method.values():
        for trial in trials:
            for r in trial:
                if r["video"] not in videos:
                    videos.append(r["video"])
    if len(videos) <= 1:
        return []

    lines = [
        "", f"## Per-Video Accuracy — {_SCORER_LABELS.get(scorer, scorer)}", "",
        "| Video | " + " | ".join(methods) + " |",
        "|-------|" + "------|" * len(methods),
    ]
    for v in videos:
        cells = []
        for m in methods:
            scores = [_score_of(r, scorer) for trial in raw_by_method[m]
                      for r in trial if r["video"] == v]
            cells.append(f"{sum(scores) / len(scores):.3f}" if scores else "—")
        lines.append(f"| {Path(v).name} | " + " | ".join(cells) + " |")
    return lines


def _break_even_lines(results_by_method: dict[str, dict],
                      raw_by_method: Optional[dict[str, list[list[dict]]]]) -> list[str]:
    """Token break-even of agent (prebuild + marginal) vs vlm_direct (flat per-Q).

    The agent's economics are 'structure once, reuse across questions' — the
    flat-rate comparison alone hides this, so report the crossover point.
    """
    if not raw_by_method or "agent" not in results_by_method \
            or "vlm_direct" not in results_by_method:
        return []

    agent_marginal = results_by_method["agent"]["avg_tokens_per_q"]
    vlm_per_q = results_by_method["vlm_direct"]["avg_tokens_per_q"]

    # Average one-time prebuild cost per video, reconstructed from per-row
    # amortized shares (share * n_questions of that video in that trial).
    totals = []
    for trial in raw_by_method["agent"]:
        by_video: dict[str, list[float]] = {}
        for r in trial:
            by_video.setdefault(r["video"], []).append(r.get("prebuild_share", 0.0))
        totals += [shares[0] * len(shares) for shares in by_video.values()]
    prebuild_video = _mean(totals)
    if prebuild_video <= 0:
        return []

    if vlm_per_q <= agent_marginal:
        return [
            f"- **Break-even vs vlm_direct**: none — agent marginal cost "
            f"({agent_marginal} tokens/Q) ≥ vlm_direct ({vlm_per_q} tokens/Q), "
            f"so the {int(prebuild_video)}-token prebuild never pays back at this "
            f"question volume"
        ]
    k = math.ceil(prebuild_video / (vlm_per_q - agent_marginal))
    return [
        f"- **Break-even vs vlm_direct**: prebuild ≈ {int(prebuild_video)} "
        f"tokens/video (one-time); marginal {agent_marginal} vs {vlm_per_q} "
        f"tokens/Q → agent's cumulative cost drops below vlm_direct from "
        f"~{k} questions per video onward"
    ]


def _build_report(results_by_method: dict[str, dict], n_runs: int,
                  video_path: str, bench_path: str,
                  raw_by_method: Optional[dict[str, list[list[dict]]]] = None,
                  scorers: tuple[str, ...] = SCORERS,
                  skip_explore_cats: frozenset = frozenset()) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Benchmark Results",
        "",
        f"> Video: `{video_path}`  |  Benchmark: `{bench_path}`  "
        f"|  Runs: {n_runs}  |  Generated: {ts}",
        "",
    ]
    if skip_explore_cats:
        lines += [
            f"> ⚠️ **agent_v2 ORACLE routing**: categories {sorted(skip_explore_cats)} "
            "were routed to the no-explore variant (answer from L0 + memory search "
            "only) **using the gold dimension label**. This is an UPPER BOUND — a "
            "deployable number requires a question-type classifier, not the gold label.",
            "",
        ]

    # ── Overall: one accuracy column per scorer ───────────────────────────────
    scorer_cols = " | ".join(
        f"Acc · {_SCORER_LABELS.get(s, s)}" for s in scorers
    )
    lines += [
        "## Overall Accuracy",
        "",
        f"| Method | {scorer_cols} | Avg Tool Calls | Avg Time (s) "
        f"| Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |",
        "|--------|" + "----|" * len(scorers)
        + "----------------|--------------|------|------|------|------|",
    ]
    for method, agg in results_by_method.items():
        accs = " | ".join(
            f"{agg['scorers'][s]['overall_mean']:.3f} ± {agg['scorers'][s]['overall_std']:.3f}"
            for s in scorers
        )
        tc = str(agg["avg_tool_calls"]) if method.startswith("agent") else "—"
        pb = agg.get("avg_prebuild_per_q", 0)
        lines.append(
            f"| **{method}** | {accs} | {tc} | {agg['avg_time_sec']} "
            f"| {agg.get('avg_frames_per_q', 0)} "
            f"| {agg['avg_tokens_per_q']} | {pb if pb else '—'} "
            f"| {agg.get('avg_total_tokens_per_q', agg['avg_tokens_per_q'])} |"
        )

    # ── Per-category: one sub-table per scorer ────────────────────────────────
    first_agg = next(iter(results_by_method.values()))
    categories = list(first_agg["scorers"][scorers[0]]["by_category"].keys())
    for s in scorers:
        lines += ["", f"## Per-Category Accuracy — {_SCORER_LABELS.get(s, s)}", ""]
        lines += [
            "| Category | " + " | ".join(results_by_method.keys()) + " |",
            "|----------|" + "---------|" * len(results_by_method),
        ]
        for cat in categories:
            label = _CAT_LABELS.get(cat, cat)
            vals = [
                f"{agg['scorers'][s]['by_category'][cat]['mean']:.3f}"
                f"±{agg['scorers'][s]['by_category'][cat]['std']:.3f}"
                for agg in results_by_method.values()
            ]
            lines.append(f"| {label} | " + " | ".join(vals) + " |")

    # ── Per-video: one sub-table per scorer (multi-video benchmarks only) ──────
    if raw_by_method:
        for s in scorers:
            lines += _per_video_lines(raw_by_method, s)

    lines += [
        "",
        "## Notes",
        "",
        "- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools",
        "- **agent_v2**: Lazy-memory agent — per-video init is only a sparse-frame summary + local "
        "ASR transcript; the agent then decides at runtime which time windows to explore "
        "(explore_segment builds dense captions + indexed triplets on demand), with a "
        "confidence-driven loop (rate 1-3, ≤2 explores/round, ≤3 rounds)",
        "- **agent_tiered**: Cost-aware agent — scene graph (or its summary, when >"
        f"{_TIERED_GRAPH_FULL_THRESHOLD} triplets) injected into context; the model decides at "
        "runtime whether to answer directly (one LLM call) or escalate to query/inspect tools",
        "- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only",
        "- **vlm_direct**: Samples N frames (default 4, see --vlm-frames), sends raw frames + "
        "question directly to VLM",
        "- **vlm_transcript**: vlm_direct + the local ASR transcript prepended to the prompt — "
        "fairness baseline isolating the extra modality from the architecture",
        "- **Frames/Q**: frames sent to the vision model per question (answer phase) — the "
        "guided-perception-budget metric",
        "- **Prebuild frame budget**: duration-adaptive — one frame per ~15s, clamped to [8, 24] "
        "(Charades-length clips stay at the historical 8)",
        "- **Token accounting**: all counts are real API-reported `usage` summed over every call "
        "the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully "
        "counted; VL calls include image tokens in prompt_tokens). No estimates. "
        "**Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the "
        "one-time scene-graph build over that video's questions (vlm_direct has no prebuild). "
        "Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted",
    ]
    lines += _break_even_lines(results_by_method, raw_by_method)
    if "llm" in scorers:
        lines.append(
            f"- **LLM-judge**: `{_judge_model()}` scores 0 / 0.5 / 1 against `key_facts` "
            "(partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)"
        )
    if "mmbv" in scorers:
        lines.append(
            f"- **MMBench-Video official (0-3)**: VLMEvalKit protocol replicated verbatim "
            f"(semantic-similarity integer 0-3, mean aggregation, judge failures → 0 per the "
            f"official 'all' variant; raw -1 kept in JSON). Judge model: `{_judge_model()}` "
            "(official protocol uses gpt-4-turbo; swap via JUDGE_MODEL for paper numbers)"
        )
    if "exact" in scorers:
        lines.append(
            "- **exact-match**: strict normalized EM (1/0) against `_source.en_answer`; binary uses "
            "the first yes/no, others require normalized equality (length-guarded). Verbose answers "
            "(e.g. the ReAct agent) are reduced to their canonical short form by a deterministic "
            "extraction step before EM. NOTE: extraction is unreliable on open/'X or Y' questions "
            "(see docs/em_vs_agent_analysis.md) — treat non-binary EM as a conservative reference"
        )
    lines.append(f"- Each method ran {n_runs} independent trials; mean ± std reported over trials")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Video QA benchmark runner")
    parser.add_argument(
        "--video", default=None,
        help="Fallback video path for questions that omit a 'video' field. "
             "Multi-video benchmarks carry per-question 'video' and don't need this.",
    )
    parser.add_argument("--benchmark", default="benchmarks/cn_video_qa_v1.json")
    parser.add_argument("--methods", default="agent,rag_only,vlm_direct")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", default="docs/benchmark_results.md")
    parser.add_argument(
        "--categories",
        default="",
        help="Comma-separated categories to run (default: all)",
    )
    parser.add_argument(
        "--scorers", default=",".join(SCORERS),
        help=f"Comma-separated scorers to run (default: all). Options: {', '.join(SCORERS)}. "
             "Each answer is scored once per scorer and reported in its own column.",
    )
    parser.add_argument(
        "--vlm-frames", type=int, default=None,
        help=f"Frame count for the vlm_direct baseline (default "
             f"{_VLM_DIRECT_FRAME_COUNT}). Long-video benchmarks should also "
             f"report a higher budget (e.g. 8) for baseline fairness.",
    )
    parser.add_argument(
        "--answer-mode", choices=["short", "verbose"], default="short",
        help="short: constrain methods to a terse answer (exact-match setup). "
             "verbose: product-default answers (agent cites evidence, baselines give "
             "2-4 sentences) — use for an LLM-judge comparison against the old runs.",
    )
    parser.add_argument(
        "--skip-explore-categories", default="",
        help="agent_v2 only: comma-separated L2 categories routed to the "
             "no-explore variant (answer from L0 + memory search, no window "
             "zooming). ROUTING USES THE GOLD CATEGORY LABEL = oracle/upper-bound; "
             "a real classifier is needed for a deployable number. e.g. TR,FP-C,LR",
    )
    args = parser.parse_args()

    short_answer = args.answer_mode == "short"
    skip_explore_cats = frozenset(
        c.strip() for c in args.skip_explore_categories.split(",") if c.strip())
    scorers = tuple(s.strip() for s in args.scorers.split(",") if s.strip())
    unknown = [s for s in scorers if s not in ALL_SCORERS]
    if unknown:
        print(f"ERROR: unknown scorer(s) {unknown}; valid: {', '.join(ALL_SCORERS)}")
        sys.exit(1)
    primary = scorers[0]  # used for the one-line console summary

    # ── sanity checks ─────────────────────────────────────────────────────────
    from src.config import get_settings
    cfg = get_settings()
    if not cfg.dashscope_api_key and cfg.backend == "dashscope":
        print("ERROR: DASHSCOPE_API_KEY not set. Please export it or add to .env")
        sys.exit(1)

    bench_path = Path(args.benchmark)
    if not bench_path.exists():
        print(f"ERROR: benchmark file not found: {bench_path}")
        sys.exit(1)

    questions: list[dict] = json.loads(bench_path.read_text(encoding="utf-8"))

    if args.categories:
        cats = set(args.categories.split(","))
        questions = [q for q in questions if q["category"] in cats]
        print(f"Filtered to categories {cats}: {len(questions)} questions")

    # Resolve the set of videos referenced by the benchmark (per-question
    # 'video' field, falling back to --video). Drives single- vs multi-video mode.
    unique_videos = sorted({(q.get("video") or args.video) for q in questions})
    if any(v is None for v in unique_videos):
        print("ERROR: some questions have no 'video' field and --video was not set")
        sys.exit(1)
    video_label = unique_videos[0] if len(unique_videos) == 1 \
        else f"{len(unique_videos)} videos"

    methods = [m.strip() for m in args.methods.split(",")]
    results_by_method: dict[str, dict] = {}
    raw_by_method: dict[str, list[list[dict]]] = {}

    print(f"\n{'='*60}")
    print(f"  Video QA Benchmark")
    print(f"  Video(s) : {video_label}")
    print(f"  Questions: {len(questions)}")
    print(f"  Methods  : {methods}")
    print(f"  Runs     : {args.runs}")
    print(f"  Scorers  : {list(scorers)}")
    print(f"  Ans mode : {args.answer_mode}")
    if skip_explore_cats:
        print(f"  Skip-explore (ORACLE routing, upper bound): {sorted(skip_explore_cats)}")
    print(f"{'='*60}\n")

    for method in methods:
        print(f"\n{'─'*60}")
        print(f"  METHOD: {method.upper()}")
        print(f"{'─'*60}")

        all_trials: list[list[dict]] = []
        for run_i in range(args.runs):
            print(f"\n  Run {run_i + 1}/{args.runs}")
            trial = run_trial(method, args.video, questions, scorers, short_answer,
                              vlm_frames=args.vlm_frames,
                              skip_explore_categories=skip_explore_cats)
            all_trials.append(trial)
            acc = _mean([_score_of(r, primary) for r in trial])
            print(f"  → Run accuracy ({primary}): {acc:.3f}")

        agg = _aggregate(all_trials, scorers)
        results_by_method[method] = agg
        raw_by_method[method] = all_trials

        p = agg["scorers"][primary]
        print(f"\n  {method} summary ({primary}): "
              f"{p['overall_mean']:.3f} ± {p['overall_std']:.3f}")

    # ── Print summary table ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"  (accuracy shown for scorer: {primary}; full report has all scorers)")
    print(f"\n{'Method':<15} {'Accuracy':>15} {'Time(s)':>10} "
          f"{'Tok/Q':>8} {'+Build':>8} {'=Total':>8}")
    print("─" * 70)
    for method, agg in results_by_method.items():
        p = agg["scorers"][primary]
        acc = f"{p['overall_mean']:.3f}±{p['overall_std']:.3f}"
        print(f"{method:<15} {acc:>15} {agg['avg_time_sec']:>10.1f} "
              f"{agg['avg_tokens_per_q']:>8} {agg['avg_prebuild_per_q']:>8} "
              f"{agg['avg_total_tokens_per_q']:>8}")

    # Per-category breakdown (primary scorer)
    print(f"\n{'Category':<16}", end="")
    for method in methods:
        print(f" {method:>15}", end="")
    print()
    print("─" * (16 + 16 * len(methods)))
    first_agg = next(iter(results_by_method.values()))
    for cat in first_agg["scorers"][primary]["by_category"]:
        label = _CAT_LABELS.get(cat, cat)
        print(f"{label:<16}", end="")
        for method in methods:
            c = results_by_method[method]["scorers"][primary]["by_category"][cat]
            print(f" {c['mean']:.3f}±{c['std']:.3f}  ", end="")
        print()

    # ── Write markdown report ─────────────────────────────────────────────────
    report = _build_report(results_by_method, args.runs, video_label,
                           args.benchmark, raw_by_method, scorers,
                           skip_explore_cats=skip_explore_cats)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\n  Report written to: {out_path}")
    print(f"{'='*60}\n")

    # Also dump raw JSON for later analysis — include per-question answers and
    # both scores so llm-vs-exact disagreements can be audited.
    raw_dump = {
        method: [
            [
                {k: r.get(k) for k in
                 ("id", "video", "category", "question", "answer",
                  "answer_short", "scores", "tool_calls", "tokens",
                  "tokens_llm", "tokens_vl", "frames_touched", "prebuild_share")}
                for r in trial
            ]
            for trial in trials
        ]
        for method, trials in raw_by_method.items()
    }
    raw_out = out_path.with_suffix(".json")
    raw_out.write_text(
        json.dumps({"meta": {"video": video_label, "videos": unique_videos,
                             "runs": args.runs, "scorers": list(scorers)},
                    "results": results_by_method,
                    "raw": raw_dump}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
