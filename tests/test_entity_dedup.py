"""
Test: entity naming stabilization across VLM batches.

Verifies that _cross_dedup_with_graph merges entities when their labels
are ≥ 85% similar (same type, any timestamps).

Run:
    pytest tests/test_entity_dedup.py -v -s
"""
from __future__ import annotations

import pytest

from src.scene_graph.graph import Entity, SceneGraph


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_entity_dict(
    label: str,
    etype: str = "person",
    first_seen: float = 0.0,
    last_seen: float = 5.0,
) -> dict:
    return {
        "id":         label,
        "type":       etype,
        "label":      label,
        "attributes": {},
        "first_seen": first_seen,
        "last_seen":  last_seen,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_same_label_not_duplicated() -> None:
    """Exact same label → merged, not added as new entity."""
    from src.scene_graph.builder import _cross_dedup_with_graph

    existing: dict[str, Entity] = {
        "man in red jacket": Entity("man in red jacket", "person"),
    }
    new_entities = [_make_entity_dict("man in red jacket", "person")]

    truly_new, remap = _cross_dedup_with_graph(new_entities, existing, threshold=0.85)

    assert len(truly_new) == 0, "Exact match should be merged, not added as new"
    assert remap.get("man in red jacket") == "man in red jacket"


def test_similar_label_merged() -> None:
    """Labels like 'man in red jacket' and 'the man in red jacket' should be merged."""
    from src.scene_graph.builder import _cross_dedup_with_graph

    existing: dict[str, Entity] = {
        "man in red jacket": Entity("man in red jacket", "person"),
    }
    # VLM adds a "the " prefix — should still be similar enough
    new_entities = [_make_entity_dict("the man in red jacket", "person")]

    truly_new, remap = _cross_dedup_with_graph(new_entities, existing, threshold=0.75)

    assert len(truly_new) == 0, "Similar label should be merged with existing"
    assert "the man in red jacket" in remap


def test_different_label_not_merged() -> None:
    """Clearly different labels (< 85% similarity) must remain separate."""
    from src.scene_graph.builder import _cross_dedup_with_graph

    existing: dict[str, Entity] = {
        "man in red jacket": Entity("man in red jacket", "person"),
    }
    new_entities = [_make_entity_dict("dog on the floor", "person")]

    truly_new, remap = _cross_dedup_with_graph(new_entities, existing, threshold=0.85)

    assert len(truly_new) == 1, "Different entity should not be merged"
    assert "dog on the floor" not in remap


def test_different_type_not_merged() -> None:
    """Same label string but different type → NOT merged."""
    from src.scene_graph.builder import _cross_dedup_with_graph

    existing: dict[str, Entity] = {
        "living room": Entity("living room", "place"),
    }
    new_entities = [_make_entity_dict("living room", "object")]

    truly_new, remap = _cross_dedup_with_graph(new_entities, existing, threshold=0.85)

    assert len(truly_new) == 1, "Different entity type should not be merged"


def test_cross_batch_dedup_reduces_graph_size() -> None:
    """
    Simulate two VLM batches that name the same person differently.
    After both batches the graph should have 1 entity, not 2.
    """
    from src.scene_graph.builder import _cross_dedup_with_graph
    from src.scene_graph.graph import SceneGraph, Triplet

    g = SceneGraph()
    # Batch 1 adds the canonical name
    g.add_entity("man in red jacket", "person", first_seen=0.0, last_seen=5.0)
    g.add_triplet(Triplet("man in red jacket", "standing_on", "living room", 0.0, 5.0))

    person_count_before = len([
        n for n, e in g.entities.items() if e.entity_type == "person"
    ])

    # Batch 2 finds the same person with a slightly different label
    batch2_entities = [_make_entity_dict("a man in red jacket", "person", 5.0, 10.0)]
    truly_new, remap = _cross_dedup_with_graph(
        batch2_entities, g.entities, threshold=0.75
    )

    # Don't add the remapped entity; only add truly_new
    for ent in truly_new:
        g.add_entity(ent["label"], ent["type"])

    person_count_after = len([
        n for n, e in g.entities.items() if e.entity_type == "person"
    ])

    print(f"\nPerson entities before: {person_count_before}, after: {person_count_after}")
    print(f"Remap: {remap}")
    assert person_count_after == person_count_before, (
        f"Cross-batch dedup should prevent duplicate person entities "
        f"({person_count_before} before → {person_count_after} after)"
    )


def test_attributes_merged_on_dedup() -> None:
    """When an entity is merged, its attributes should be added to the existing one."""
    from src.scene_graph.builder import _cross_dedup_with_graph

    existing_ent = Entity("man in red jacket", "person", attributes={"color": "yellow shirt"})
    existing: dict[str, Entity] = {"man in red jacket": existing_ent}

    new_entities = [{
        "id":         "man in red jacket",
        "type":       "person",
        "label":      "man in red jacket",
        "attributes": {"holding": "green tool"},
        "first_seen": 0.0,
        "last_seen":  10.0,
    }]

    truly_new, _ = _cross_dedup_with_graph(new_entities, existing, threshold=0.85)

    assert len(truly_new) == 0
    assert existing_ent.attributes.get("holding") == "green tool", (
        "Merged entity attributes should be propagated to existing entity"
    )
