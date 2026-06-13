"""
Real scene graph integration tests — DashScope + test1.mp4.

These tests call the actual DashScope API and require:
  - DASHSCOPE_API_KEY set in the environment
  - data/videos/test1.mp4 present on disk

Run with:
    DASHSCOPE_API_KEY=sk-xxx pytest tests/test_scene_graph_real.py -v -s

The final test prints the full scene graph JSON and a token cost estimate.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

# ── markers ───────────────────────────────────────────────────────────────────

TEST_VIDEO = Path(__file__).parent.parent / "data" / "videos" / "test1.mp4"

video_available = pytest.mark.skipif(
    not TEST_VIDEO.exists(),
    reason=f"test video not found: {TEST_VIDEO}",
)
dashscope_required = pytest.mark.skipif(
    not os.getenv("DASHSCOPE_API_KEY"),
    reason="DASHSCOPE_API_KEY not set",
)


# ── tests ─────────────────────────────────────────────────────────────────────

@dashscope_required
@video_available
def test_build_scene_graph_real_dashscope():
    """
    Full pipeline: extract 4 keyframes → build scene graph via DashScope VLM
    → verify entities and relations are populated.
    """
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph

    session = VideoSession(str(TEST_VIDEO))

    # Step 1: extract keyframes
    extract = make_extract_keyframes(session)
    kf_result = json.loads(extract.invoke({"strategy": "uniform", "count": 4}))
    assert kf_result["total_cached"] == 4
    print(f"\n[keyframes] {kf_result['timestamps']}")

    # Step 2: build scene graph
    build = make_build_scene_graph(session)
    t0 = time.time()
    sg_result = json.loads(build.invoke({
        "frame_ids": ",".join(kf_result["frame_ids"]),
        "focus_entities": "",
    }))
    elapsed = time.time() - t0

    print(f"\n[build_scene_graph] mode={sg_result.get('_mode')}")
    print(f"[build_scene_graph] nodes_added={sg_result['nodes_added']}, "
          f"edges_added={sg_result['edges_added']}")
    print(f"[build_scene_graph] elapsed={elapsed:.1f}s")
    print(f"[graph_summary]\n{sg_result['graph_summary']}")

    assert "new_triplets" in sg_result
    assert "graph_summary" in sg_result
    assert sg_result.get("_mode") == "real", (
        f"Expected real mode but got {sg_result.get('_mode')} — "
        f"check DASHSCOPE_API_KEY and frame paths"
    )
    # VLM should find at least one entity in a 14-second video
    assert sg_result["nodes_added"] >= 1, "VLM found no entities — check prompt or API response"


@dashscope_required
@video_available
def test_scene_graph_json_output():
    """
    Full pipeline end-to-end — prints the complete scene graph JSON.
    This is the 'show me the result' test the user requested.
    """
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph
    from src.config import get_settings

    cfg = get_settings()
    session = VideoSession(str(TEST_VIDEO))

    extract = make_extract_keyframes(session)
    json.loads(extract.invoke({"strategy": "uniform", "count": 4}))

    build = make_build_scene_graph(session)
    sg_result = json.loads(build.invoke({"frame_ids": "*", "focus_entities": ""}))

    sg_dict = session.scene_graph.to_dict()

    print("\n" + "=" * 60)
    print("SCENE GRAPH JSON OUTPUT")
    print("=" * 60)
    print(json.dumps(sg_dict, ensure_ascii=False, indent=2))
    print("=" * 60)
    print(f"Total entities : {len(sg_dict['entities'])}")
    print(f"Total triplets : {len(sg_dict['triplets'])}")
    print(f"Model used     : {cfg.models.vl.model_name}")
    print(f"Backend        : {cfg.backend}")
    print("=" * 60)
    print("\nToken cost estimate (qwen-vl-plus-latest, 4 frames @ 1280px):")
    print("  Input : ~4 × 1500 + 600 (prompt) ≈ 6600 tokens  ≈ ¥0.053")
    print("  Output: ~500 tokens                              ≈ ¥0.004")
    print("  Total : ≈ ¥0.057 / call  (verify against DashScope pricing)")

    assert len(sg_dict["entities"]) > 0
    assert len(sg_dict["triplets"]) > 0


@dashscope_required
@video_available
def test_inspect_frame_real_dashscope():
    """inspect_frame with real VLM updates scene graph and returns an answer."""
    from src.memory.session import VideoSession
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.frame_inspector import make_inspect_frame

    session = VideoSession(str(TEST_VIDEO))
    extract = make_extract_keyframes(session)
    json.loads(extract.invoke({"strategy": "uniform", "count": 4}))

    first_ts = list(session.cached_frames.values())[0].timestamp
    inspect = make_inspect_frame(session)
    result = json.loads(inspect.invoke({
        "timestamp": first_ts,
        "question": "What people are in the frame? What are they doing?",
    }))

    print(f"\n[inspect answer] {result['answer']}")
    print(f"[inspect entities] {result['new_entities']}")

    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 5
    assert result["frame_id"] is not None
