"""
End-to-end behavior tests for the FastAPI service (offline, mock mode).

Per CLAUDE.md: every product mode needs at least one behavior test, and mock
output must stay labeled + fabrication-free. These tests run without an API
key, a real video, or network access — the mock session drives the real v1
tool loop (tools fail loud on the empty file; the scripted model still ends
with the [MOCK] placeholder).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import app, _REGISTRY
from src.tools.keyframe import _frame_dir


@pytest.fixture
def client():
    _REGISTRY.clear()
    with TestClient(app) as c:
        yield c
    _REGISTRY.clear()


@pytest.fixture
def video_file(tmp_path: Path) -> str:
    """An empty placeholder file: passes the existence check; frame extraction
    fails loud inside the tool loop, which is exactly the offline contract."""
    p = tmp_path / "test.mp4"
    p.write_bytes(b"")
    return str(p)


def _create_mock_session(client: TestClient, video_file: str) -> str:
    resp = client.post("/sessions", json={"video_path": video_file, "mock": True})
    assert resp.status_code == 201
    body = resp.json()
    assert body["mock"] is True
    return body["session_id"]


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_rejects_missing_video(client: TestClient) -> None:
    resp = client.post("/sessions",
                       json={"video_path": "does/not/exist.mp4", "mock": True})
    assert resp.status_code == 400


def test_mock_ask_is_labeled_and_fabrication_free(client: TestClient,
                                                  video_file: str) -> None:
    sid = _create_mock_session(client, video_file)
    resp = client.post(f"/sessions/{sid}/ask",
                       json={"question": "what happens in the video?"})
    assert resp.status_code == 200
    body = resp.json()
    # Labeled mock answer, no fabricated scene-graph evidence
    assert "[MOCK]" in body["answer"]
    assert re.search(r"--\[.+\]-->", body["answer"]) is None
    # The scripted mock drives the real tool loop
    names = [tc["name"] for tc in body["tool_calls"]]
    assert "extract_keyframes" in names
    assert "query_scene_graph" in names


def test_session_state_tracks_questions(client: TestClient,
                                        video_file: str) -> None:
    sid = _create_mock_session(client, video_file)
    client.post(f"/sessions/{sid}/ask", json={"question": "q1"})
    resp = client.get(f"/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["questions_asked"] == 1


def test_unknown_session_is_404(client: TestClient) -> None:
    assert client.get("/sessions/nope").status_code == 404
    assert client.post("/sessions/nope/ask",
                       json={"question": "?"}).status_code == 404
    assert client.delete("/sessions/nope").status_code == 404


def test_delete_removes_session_and_frame_dir(client: TestClient,
                                              video_file: str) -> None:
    sid = _create_mock_session(client, video_file)
    session = _REGISTRY[sid].session
    frame_dir = _frame_dir(session)
    frame_dir.mkdir(parents=True, exist_ok=True)
    (frame_dir / "probe.jpg").write_bytes(b"x")

    resp = client.delete(f"/sessions/{sid}")
    assert resp.status_code == 200
    assert not frame_dir.exists()
    # Session is really gone
    assert client.post(f"/sessions/{sid}/ask",
                       json={"question": "?"}).status_code == 404


def test_stream_emits_trace_then_labeled_answer(client: TestClient,
                                                video_file: str) -> None:
    sid = _create_mock_session(client, video_file)
    with client.stream("GET", f"/sessions/{sid}/ask/stream",
                       params={"question": "what happens?"}) as resp:
        assert resp.status_code == 200
        events = [json.loads(line[len("data: "):])
                  for line in resp.iter_lines() if line.startswith("data: ")]
    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert types[-1] == "answer"
    assert "[MOCK]" in events[-1]["answer"]
