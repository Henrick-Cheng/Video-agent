"""
Test: Chinese scene graph retrieval with jieba multi-strategy matching.

Builds a synthetic scene graph with realistic entities and relations,
then fires 10 Chinese queries and checks hit rate.

Target: ≥ 80% hit rate (≥ 8 / 10 queries find at least 1 triplet).

Run:
    pytest tests/test_query_chinese.py -v -s
"""
from __future__ import annotations

import pytest

from src.scene_graph.graph import SceneGraph, Triplet


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def game_graph() -> SceneGraph:
    """Scene graph mimicking the test1.mp4 game lobby."""
    g = SceneGraph()

    triplets = [
        Triplet("骑着骡子打鸟", "站在", "游戏大厅", 0.0, 14.0, 0.95),
        Triplet("鱿鱼不是鱼",   "站在", "游戏大厅", 0.0, 14.0, 0.92),
        Triplet("不si的土卜鼠", "站在", "游戏大厅", 0.0, 14.0, 0.91),
        Triplet("允崽",         "站在", "游戏大厅", 0.0, 14.0, 0.90),
        Triplet("骑着骡子打鸟", "持有", "绿色武器",  2.0,  8.0, 0.88),
        Triplet("不si的土卜鼠", "持有", "蓝色枪械",  2.0,  8.0, 0.85),
        Triplet("允崽",         "携带", "德国国旗头盔", 4.0, 14.0, 0.80),
        Triplet("黑色跑车",      "停在", "游戏大厅",   0.0, 14.0, 0.90),
        Triplet("不si的土卜鼠", "看向", "黑色跑车",   5.0, 10.0, 0.78),
        Triplet("鱿鱼不是鱼",   "属于", "蓝方战队",   0.0, 14.0, 0.95),
        Triplet("骑着骡子打鸟", "属于", "蓝方战队",   0.0, 14.0, 0.95),
    ]
    for t in triplets:
        g.add_triplet(t)

    return g


# ── Test cases ────────────────────────────────────────────────────────────────

_QUERIES: list[tuple[str, str]] = [
    # (query, description-of-expected-hit)
    ("视频里有哪些人物？",                        "人物实体查询"),
    ("游戏大厅里站着谁？",                        "站在游戏大厅"),
    ("有人拿枪吗？",                              "持有枪械"),
    ("视频中有几辆跑车？",                        "跑车相关"),
    ("不si的土卜鼠拿着什么武器？",               "精确实体名+持有"),
    ("骑着骡子打鸟在做什么？",                   "精确实体名"),
    ("谁属于蓝方战队？",                          "属于关系"),
    ("有人带头盔吗？",                            "携带头盔"),
    ("谁在看跑车？",                              "看向跑车"),
    ("鱿鱼不是鱼站在哪里？",                     "精确实体名+位置"),
]


def test_chinese_retrieval_hit_rate(game_graph: SceneGraph) -> None:
    """≥ 8/10 queries must find at least one triplet."""
    from src.scene_graph.retriever import retrieve_triplets

    hits = 0
    for query, desc in _QUERIES:
        result = retrieve_triplets(query, game_graph, top_k=5)
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
        "Failing queries may need stopword tuning or jieba user-dict coverage."
    )


def test_exact_entity_name_match(game_graph: SceneGraph) -> None:
    """Querying with an entity's exact name must always find triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    for entity_name in ["不si的土卜鼠", "骑着骡子打鸟", "鱿鱼不是鱼", "允崽"]:
        result = retrieve_triplets(entity_name, game_graph, top_k=5)
        assert result["found"], (
            f"Exact entity name '{entity_name}' should always find triplets"
        )


def test_relation_verb_match(game_graph: SceneGraph) -> None:
    """Querying a relation verb must find matching triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    result = retrieve_triplets("持有", game_graph, top_k=5)
    assert result["found"], "Relation verb '持有' must match triplets"
    relations = [t["relation"] for t in result["triplets"]]
    assert "持有" in relations, "Matched triplets should include '持有' relation"


def test_found_false_returns_nearby_entities(game_graph: SceneGraph) -> None:
    """
    Even when no triplets match, nearby_entities should suggest related content.
    Query uses a term close to an entity name without being exact.
    """
    from src.scene_graph.retriever import retrieve_triplets

    # "骡子打鸟" is a partial match for "骑着骡子打鸟"
    result = retrieve_triplets("骡子", game_graph, top_k=5)
    # Either found a triplet OR nearby_entities is non-empty
    has_info = result["found"] or len(result["nearby_entities"]) > 0
    assert has_info, (
        "Query '骡子' should at least surface nearby entities containing '骡子'"
    )


def test_time_constraint_start(game_graph: SceneGraph) -> None:
    """'开头' keyword should restrict results to early-timestamp triplets."""
    from src.scene_graph.retriever import retrieve_triplets

    result = retrieve_triplets("开头谁在游戏大厅", game_graph, top_k=10)
    assert result["found"], "Time-constrained query should find early triplets"
    for t in result["triplets"]:
        # Triplets starting near t=0 should be included
        assert t["t_start"] <= 5.0, (
            f"Time filter 'start' should only return early triplets, got t_start={t['t_start']}"
        )
