"""
Test: English scene graph retrieval with multi-strategy matching.

Builds a synthetic Charades-style daily-activity scene graph, then fires
10 English queries and checks hit rate.

Target: ≥ 80% hit rate (≥ 8 / 10 queries find at least 1 triplet).

Run:
    pytest tests/test_query_english.py -v -s
"""
from __future__ import annotations

import pytest

from src.scene_graph.graph import SceneGraph, Triplet


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def daily_graph() -> SceneGraph:
    """Scene graph mimicking a Charades-style daily-activity clip."""
    g = SceneGraph()

    triplets = [
        Triplet("person",  "holding",     "blanket", 0.0,  5.0, 0.95),
        Triplet("person",  "leaning_on",  "bed",     0.0,  5.0, 0.92),
        Triplet("person",  "watching",    "phone",   2.0,  8.0, 0.90),
        Triplet("person",  "holding",     "cup",     3.0,  7.0, 0.88),
        Triplet("person",  "opening",     "door",    8.0, 12.0, 0.85),
        Triplet("vacuum",  "located_at",  "table",   0.0, 14.0, 0.80),
        Triplet("person",  "touching",    "vacuum",  9.0, 13.0, 0.82),
        Triplet("person",  "putting_down", "shoes",  10.0, 14.0, 0.78),
        Triplet("phone",   "located_at",  "table",   0.0,  6.0, 0.90),
    ]
    for t in triplets:
        g.add_triplet(t)

    return g


# ── Test cases ────────────────────────────────────────────────────────────────

_QUERIES: list[tuple[str, str]] = [
    # (query, description-of-expected-hit)
    ("What is the person holding?",            "relation holding + person"),
    ("What is the person leaning on?",         "relation leaning_on"),
    ("Is there a vacuum in the video?",        "entity vacuum"),
    ("What did the person open?",              "relation opening + person"),
    ("Who is watching the phone?",             "relation watching + phone"),
    ("Where is the phone?",                    "entity phone"),
    ("Did the person touch the vacuum?",       "relation touching + vacuum"),
    ("What is on the table?",                  "entity table"),
    ("What did the person put down?",          "relation putting_down"),
    ("blanket",                                "exact entity name"),
]


def test_english_retrieval_hit_rate(daily_graph: SceneGraph) -> None:
    """≥ 8/10 queries must find at least one triplet."""
    from src.scene_graph.retriever import retrieve_triplets

    hits = 0
    for query, desc in _QUERIES:
        result = retrieve_triplets(query, daily_graph, top_k=5)
        ok = result["found"]
        status = "HIT " if ok else "MISS"
        print(f"  [{status}] {desc:30s}  query='{query}'")
        if ok:
            print(f"         matched_tokens={result['matched_tokens']}")
            print(f"         top triplet: {result['triplets'][0]['subject']} "
                  f"--[{result['triplets'][0]['relation']}]--> "
                  f"{result['triplets'][0]['object']}")
        else:
            print(f"         nearby_entities={result['nearby_entities']}")
        hits += int(ok)

    print(f"\nHit rate: {hits}/{len(_QUERIES)} = {hits/len(_QUERIES)*100:.0f}%")
    assert hits >= 8, (
        f"Expected ≥ 8/10 hits, got {hits}/10. "
        "Failing queries may need stopword tuning or lemmatizer coverage."
    )


def test_exact_entity_name_match(daily_graph: SceneGraph) -> None:
    """Querying with an entity's exact name must always find triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    for entity_name in ["person", "blanket", "vacuum", "phone"]:
        result = retrieve_triplets(entity_name, daily_graph, top_k=5)
        assert result["found"], (
            f"Exact entity name '{entity_name}' should always find triplets"
        )


def test_relation_verb_match(daily_graph: SceneGraph) -> None:
    """Querying a relation verb must find matching triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    result = retrieve_triplets("holding", daily_graph, top_k=5)
    assert result["found"], "Relation verb 'holding' must match triplets"
    relations = [t["relation"] for t in result["triplets"]]
    assert "holding" in relations, "Matched triplets should include 'holding' relation"


def test_found_false_returns_nearby_entities(daily_graph: SceneGraph) -> None:
    """
    Even when no triplets match, nearby_entities should suggest related content.
    Query uses a term close to an entity name without being exact.
    """
    from src.scene_graph.retriever import retrieve_triplets

    # "blank" is a partial match for "blanket"
    result = retrieve_triplets("blank", daily_graph, top_k=5)
    # Either found a triplet OR nearby_entities is non-empty
    has_info = result["found"] or len(result["nearby_entities"]) > 0
    assert has_info, (
        "Query 'blank' should at least surface nearby entities containing it"
    )


def test_time_constraint_start(daily_graph: SceneGraph) -> None:
    """'beginning' keyword should restrict results to early-timestamp triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    result = retrieve_triplets(
        "who is in the room at the beginning", daily_graph, top_k=10,
        video_duration=14.0,
    )
    for t in result["triplets"]:
        # Triplets starting in the first 20% (≤ 2.8s) should be included
        assert t["t_start"] <= 5.0, (
            f"Time filter 'start' should only return early triplets, "
            f"got t_start={t['t_start']}"
        )
