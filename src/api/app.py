"""
FastAPI service — thin wrapper over the v2 agent (lazy 3-layer memory +
confidence loop).

Same architecture as main.py's product path: a session is created per video
(`prepare_l0` builds the L0 base once), questions run the v2 agent with the
L0 context prefix and the shared pseudo-call retry. Explored windows and the
triplet index persist on the session, so later questions reuse earlier work.

Mock mode (`{"mock": true}` at session creation) mirrors the CLI's `--mock`:
it runs the v1 scripted offline agent — no API key required, output is
labeled [MOCK] and fabricates no video content (see CLAUDE.md contract).

Run:
    uvicorn src.api.app:app --host 0.0.0.0 --port 8000

Endpoints:
    GET    /healthz
    POST   /sessions                     {video_path, mock=false}
    GET    /sessions/{sid}
    POST   /sessions/{sid}/ask           {question}
    GET    /sessions/{sid}/ask/stream    ?question=...   (SSE trace)
    DELETE /sessions/{sid}
"""

from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.memory.session import VideoSession

app = FastAPI(
    title="Video Agent API",
    description="Video Q&A with lazy 3-layer memory + confidence-driven exploration",
    version="0.1.0",
)


# ── Session registry ──────────────────────────────────────────────────────────
# VideoSession is not thread-safe (plain dicts/lists mutated by tools), so each
# session gets its own lock held for the duration of an ask; the registry lock
# only guards the dict itself.

class _Entry:
    def __init__(self, session: VideoSession, agent: Any, mock: bool) -> None:
        self.session = session
        self.agent = agent
        self.mock = mock
        self.lock = threading.Lock()


_REGISTRY: dict[str, _Entry] = {}
_REGISTRY_LOCK = threading.Lock()


def _get_entry(session_id: str) -> _Entry:
    with _REGISTRY_LOCK:
        entry = _REGISTRY.get(session_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id!r}")
    return entry


# ── Request/response models ───────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    video_path: str
    mock: bool = False


class AskRequest(BaseModel):
    question: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "sessions": len(_REGISTRY)}


@app.post("/sessions", status_code=201)
def create_session(req: CreateSessionRequest) -> dict:
    """Create a session for one video. Real mode builds the L0 base (global
    summary via 1 VL call + local ASR transcript) up front; mock mode skips L0
    and wires the v1 scripted offline agent (no API key needed)."""
    from src.agents.react_agent import build_agent, build_agent_v2, prepare_l0

    if not Path(req.video_path).exists():
        raise HTTPException(status_code=400,
                            detail=f"video not found: {req.video_path}")

    session = VideoSession(video_path=req.video_path)
    if req.mock:
        agent = build_agent(session, use_mock=True)
    else:
        # Runs in FastAPI's worker threadpool (sync endpoint), so the VL call +
        # ASR transcription don't block the event loop.
        prepare_l0(session, verbose=False)
        agent = build_agent_v2(session, short_answer=False)

    entry = _Entry(session, agent, req.mock)
    with _REGISTRY_LOCK:
        _REGISTRY[session.session_id] = entry

    return {
        "session_id": session.session_id,
        "video_path": session.video_path,
        "mock": req.mock,
        "duration_sec": session.duration_sec,
        "summary_ready": bool(session.global_summary),
        "transcript_lines": len(session.transcript or []),
    }


@app.get("/sessions/{session_id}")
def session_state(session_id: str) -> dict:
    """Current memory state: explored windows, graph size, question history."""
    entry = _get_entry(session_id)
    s = entry.session
    return {
        "session_id": s.session_id,
        "video_path": s.video_path,
        "mock": entry.mock,
        "duration_sec": s.duration_sec,
        "summary_ready": bool(s.global_summary),
        "transcript_lines": len(s.transcript or []),
        "explored_windows": s.explored_windows(),
        "entities": len(s.scene_graph.entities),
        "triplets": len(s.scene_graph),
        "questions_asked": len(s.query_history),
    }


def _user_text(entry: _Entry, question: str) -> str:
    from src.agents.react_agent import build_l0_context
    return question if entry.mock else build_l0_context(entry.session) + question


def _recursion_limit(entry: _Entry) -> int:
    from src.agents.react_agent import get_recursion_limit
    return get_recursion_limit(entry.agent, v2=not entry.mock)


@app.post("/sessions/{session_id}/ask")
def ask(session_id: str, req: AskRequest) -> dict:
    """Answer one question. Memory (explored windows + triplet index) persists
    on the session, so related follow-ups often answer from free search alone."""
    from src.agents.react_agent import invoke_with_retry

    entry = _get_entry(session_id)
    with entry.lock:
        entry.session.add_query(req.question)
        result = invoke_with_retry(
            entry.agent, _user_text(entry, req.question), _recursion_limit(entry))

        s = entry.session
        tool_calls = [
            {"name": tc["name"], "args": tc.get("args", {})}
            for m in result["messages"]
            if getattr(m, "type", "") == "ai"
            for tc in (getattr(m, "tool_calls", None) or [])
        ]
        return {
            "session_id": session_id,
            "question": req.question,
            "answer": result["messages"][-1].content,
            "tool_calls": tool_calls,
            "explored_windows": s.explored_windows(),
            "entities": len(s.scene_graph.entities),
            "triplets": len(s.scene_graph),
        }


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/sessions/{session_id}/ask/stream")
def ask_stream(session_id: str, question: str) -> StreamingResponse:
    """Stream the reasoning trace as Server-Sent Events: one `tool_call` /
    `observation` event per agent step, then a final `answer` event.

    Note: the streaming path reports a pseudo-call final message as-is (as an
    `answer` event with `pseudo_call: true`) instead of silently re-asking —
    the non-streaming /ask endpoint applies the corrective retry."""
    from src.agents.react_agent import looks_like_pseudo_call

    entry = _get_entry(session_id)

    def gen() -> Iterator[str]:
        with entry.lock:
            entry.session.add_query(question)
            final_answer = ""
            for update in entry.agent.stream(
                {"messages": [("user", _user_text(entry, question))]},
                config={"recursion_limit": _recursion_limit(entry)},
                stream_mode="updates",
            ):
                for node, payload in update.items():
                    for msg in (payload or {}).get("messages", []):
                        mtype = getattr(msg, "type", "")
                        if mtype == "ai":
                            for tc in getattr(msg, "tool_calls", None) or []:
                                yield _sse({"type": "tool_call",
                                            "name": tc["name"],
                                            "args": tc.get("args", {})})
                            if msg.content:
                                final_answer = msg.content
                        elif mtype == "tool":
                            obs = str(getattr(msg, "content", ""))
                            yield _sse({"type": "observation",
                                        "content": obs[:600]})
            s = entry.session
            yield _sse({
                "type": "answer",
                "answer": final_answer,
                "pseudo_call": looks_like_pseudo_call(final_answer),
                "explored_windows": s.explored_windows(),
                "entities": len(s.scene_graph.entities),
                "triplets": len(s.scene_graph),
            })

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    """Drop the session and remove its extracted-frame directory from disk."""
    from src.tools.keyframe import _frame_dir

    entry = _get_entry(session_id)
    with _REGISTRY_LOCK:
        _REGISTRY.pop(session_id, None)
    frame_dir = _frame_dir(entry.session)
    if frame_dir.exists():
        shutil.rmtree(frame_dir, ignore_errors=True)
    return {"deleted": session_id}
