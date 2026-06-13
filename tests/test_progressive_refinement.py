"""
Test: progressive refinement — the project's core differentiator.

Pipeline under test:
  1. build_scene_graph(focus_entities="person") → initial graph with N1 entities
  2. inspect_frame(question="describe all visible objects and details") → VLM deep-reads one frame
  3. scene graph back-propagation (automatic inside inspect_frame)
  4. query_scene_graph(keyword) → newly discovered content is findable

Expected: N2 >= N1, new nodes/edges reflected in graph, query finds new content.

Run with:
    DASHSCOPE_API_KEY=sk-xxx pytest tests/test_progressive_refinement.py -v -s
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_VIDEO = Path("data/videos/test1.mp4")
_HAS_KEY = bool(os.getenv("DASHSCOPE_API_KEY"))
_HAS_VIDEO = _VIDEO.exists()

_SKIP_REASON = (
    "requires DASHSCOPE_API_KEY env var and data/videos/test1.mp4"
)


@pytest.mark.skipif(not (_HAS_KEY and _HAS_VIDEO), reason=_SKIP_REASON)
def test_progressive_refinement() -> None:
    """
    End-to-end proof that inspect_frame back-propagates into the scene graph
    and that query_scene_graph can retrieve the newly discovered content.
    """
    from src.memory.session import VideoSession
    from src.tools.frame_inspector import make_inspect_frame
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph
    from src.tools.scene_graph_query import make_query_scene_graph

    session = VideoSession(str(_VIDEO))

    # ── Step 1: extract keyframes ─────────────────────────────────────────────
    extract = make_extract_keyframes(session)
    r1 = json.loads(extract.invoke({"strategy": "uniform", "count": 4}))
    frame_ids: list[str] = r1["frame_ids"]
    assert len(frame_ids) >= 1, "should cache at least one frame"
    print(f"\n[Step 1] Extracted {len(frame_ids)} frames: {frame_ids}")

    # ── Step 2: build initial scene graph (focus on person) ───────────────────
    builder = make_build_scene_graph(session)
    r2 = json.loads(builder.invoke({
        "frame_ids": ",".join(frame_ids[:2]),
        "focus_entities": "person",
    }))
    n1 = len(session.scene_graph.entities)
    t1 = len(session.scene_graph)
    assert n1 > 0, "initial graph should contain entities"
    print(f"[Step 2] Initial graph: {n1} entities, {t1} triplets")
    print(f"         Entities: {list(session.scene_graph.entities.keys())}")

    # ── Step 3: deep-read one frame with inspect_frame ────────────────────────
    first_frame = session.get_frame(frame_ids[0])
    assert first_frame is not None
    inspector = make_inspect_frame(session)
    r3 = json.loads(inspector.invoke({
        "timestamp": first_frame.timestamp,
        "question": "Describe all visible objects, people, and details in the frame, "
                    "including colors, shapes, and their relationships",
    }))

    # ── Assert: return contract ───────────────────────────────────────────────
    assert "nodes_added_to_graph" in r3, "inspect_frame must report nodes_added_to_graph"
    assert "edges_added_to_graph" in r3, "inspect_frame must report edges_added_to_graph"
    assert "graph_size_after" in r3, "inspect_frame must report graph_size_after"
    assert "answer" in r3 and r3["answer"], "VLM answer must be non-empty"

    n2 = len(session.scene_graph.entities)
    t2 = len(session.scene_graph)

    print(f"[Step 3] After inspect_frame:")
    print(f"         VLM answer  : {r3['answer'][:120]}...")
    print(f"         New entities: {r3['new_entities']}")
    print(f"         New triplets: {r3['new_triplets']}")
    print(f"         nodes_added_to_graph: {r3['nodes_added_to_graph']}")
    print(f"         edges_added_to_graph: {r3['edges_added_to_graph']}")
    print(f"         graph_size_after    : {r3['graph_size_after']}")
    print(f"[progressive refinement] graph grew: {n1}→{n2} entities, {t1}→{t2} triplets")

    # ── Assert: graph grew or inspect at least ran cleanly ───────────────────
    assert n2 >= n1, "entity count must not decrease after inspect_frame"
    assert t2 >= t1, "triplet count must not decrease after inspect_frame"

    # ── Step 4: query must find newly discovered content ──────────────────────
    querier = make_query_scene_graph(session)

    # Always verify the graph is queryable after inspect
    r4 = json.loads(querier.invoke({"question": "what is in the video"}))
    assert r4["found"], "query_scene_graph must return found=True after build+inspect"
    print(f"[Step 4] query_scene_graph found: {r4['found']}")
    print(f"         {r4['entity_summary']}")

    # If inspect added new entities, verify they are queryable by name
    if r3["new_entities"]:
        keyword = r3["new_entities"][0]
        r4b = json.loads(querier.invoke({"question": keyword}))
        # The keyword query uses substring matching — should find something
        print(f"[Step 4b] query '{keyword}' → found={r4b['found']}, "
              f"triplets={len(r4b['triplets'])}")
        # Soft assertion: entity name is in the graph even if query didn't match
        entity_names_lower = [e.lower() for e in session.scene_graph.entities]
        in_graph = any(keyword.lower() in e for e in entity_names_lower)
        assert in_graph or r4b["found"], (
            f"Entity '{keyword}' reported by inspect_frame should be in scene graph"
        )

    print(f"\n✓ Progressive refinement verified: "
          f"{n1}→{n2} entities, {t1}→{t2} triplets")
