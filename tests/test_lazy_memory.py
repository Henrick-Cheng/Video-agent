"""Unit tests for the v2 lazy memory layers (segments, unified search, ASR text)."""

from src.memory.session import VideoSession
from src.scene_graph.retriever import search_memory
from src.perception.asr import transcript_text


def _session_with_memory() -> VideoSession:
    s = VideoSession(video_path="dummy.mp4")
    s.duration_sec = 120.0
    s.global_summary = "A man cooks pasta in a kitchen and talks to the camera."
    s.transcript = [
        {"t_start": 5.0, "t_end": 9.0, "text": "Today we are making carbonara."},
        {"t_start": 40.0, "t_end": 46.0, "text": "Never add cream to carbonara."},
    ]
    seg = s.add_segment(
        t_start=30.0, t_end=50.0,
        caption="The man cracks eggs into a bowl and whisks them with grated cheese.",
        question="what does he do with the eggs",
    )
    s.update_scene_graph(
        [{"name": "man", "type": "person"}, {"name": "eggs", "type": "object"}],
        [{"subject": "man", "relation": "holding", "object": "eggs",
          "t_start": 31.0, "t_end": 35.0, "source": f"seg:{seg.segment_id}"}],
    )
    return s


def test_add_segment_ids_and_windows():
    s = _session_with_memory()
    assert list(s.segments) == ["seg_001"]
    s.add_segment(0.0, 10.0, "Intro shot of the kitchen.")
    assert list(s.segments) == ["seg_001", "seg_002"]
    assert s.explored_windows() == [(0.0, 10.0), (30.0, 50.0)]


def test_search_memory_triplet_pulls_parent_caption():
    s = _session_with_memory()
    res = search_memory("what is the man holding", s)
    assert res["found"]
    assert any(t["subject"] == "man" for t in res["triplets"])
    # Provenance: the triplet hit must surface its parent segment caption.
    assert any("cracks eggs" in seg["caption"] for seg in res["segments"])


def test_search_memory_hits_transcript():
    s = _session_with_memory()
    res = search_memory("does he add cream to the carbonara", s)
    assert any("cream" in h["text"] for h in res["transcript_hits"])


def test_search_memory_empty_session():
    s = VideoSession(video_path="dummy.mp4")
    res = search_memory("anything at all", s)
    assert res["found"] is False
    assert res["segments"] == [] and res["transcript_hits"] == []


def test_transcript_text_windowing_and_truncation():
    tr = [{"t_start": float(i), "t_end": i + 1.0, "text": f"line {i}"}
          for i in range(10)]
    full = transcript_text(tr)
    assert "line 0" in full and "line 9" in full
    windowed = transcript_text(tr, t_start=4.0, t_end=6.0)
    assert "line 4" in windowed and "line 9" not in windowed
    truncated = transcript_text(tr, max_chars=30)
    assert "truncated" in truncated
