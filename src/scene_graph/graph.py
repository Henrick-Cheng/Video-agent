"""
Temporal scene graph data structures.

Triplet format: <subject, relation, object, t_start, t_end>
The SceneGraph acts as the Agent's structured working memory throughout a session.

v2 change: Entity now carries first_seen / last_seen (added for VLM back-propagation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    name: str
    entity_type: str = "object"           # "object" | "person" | "place" | "other"
    attributes: dict[str, str] = field(default_factory=dict)
    first_seen: float = 0.0               # earliest timestamp this entity was observed
    last_seen: float = 0.0                # latest timestamp this entity was observed


@dataclass
class Triplet:
    subject: str
    relation: str
    object: str
    t_start: float
    t_end: float
    confidence: float = 1.0
    source: str = "vlm"                   # "vlm" | "inspector"
    frame_id: Optional[str] = None

    def to_text(self) -> str:
        return (
            f"({self.subject}) --[{self.relation}]--> ({self.object}) "
            f"@ [{self.t_start:.1f}s, {self.t_end:.1f}s]"
        )


class SceneGraph:
    """
    In-memory temporal scene graph for a single video session.

    Entities are stored by name; edges are stored as a flat list of Triplets.
    Deduplication is done on (subject, relation, object, t_start, t_end).
    """

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.triplets: list[Triplet] = []

    # ── mutation ──────────────────────────────────────────────────────────────

    def add_entity(
        self,
        name: str,
        entity_type: str = "object",
        attributes: Optional[dict[str, str]] = None,
        first_seen: float = 0.0,
        last_seen: float = 0.0,
    ) -> bool:
        """Add or merge an entity. Returns True if newly added."""
        if name not in self.entities:
            self.entities[name] = Entity(
                name, entity_type, attributes or {}, first_seen, last_seen
            )
            return True
        e = self.entities[name]
        if attributes:
            e.attributes.update(attributes)
        if first_seen and (e.first_seen == 0.0 or first_seen < e.first_seen):
            e.first_seen = first_seen
        if last_seen > e.last_seen:
            e.last_seen = last_seen
        return False

    def add_triplet(self, triplet: Triplet) -> bool:
        """
        Add a triplet, deduplicating by (subject, relation, object, t_start, t_end).
        Returns True if the triplet was new and inserted.
        """
        key = (triplet.subject, triplet.relation, triplet.object,
               triplet.t_start, triplet.t_end)
        for existing in self.triplets:
            if (existing.subject, existing.relation, existing.object,
                    existing.t_start, existing.t_end) == key:
                return False
        self.triplets.append(triplet)
        self.add_entity(triplet.subject)
        self.add_entity(triplet.object)
        return True

    # ── query ─────────────────────────────────────────────────────────────────

    def get_triplets_for_entities(self, entities: list[str]) -> list[Triplet]:
        """Return all triplets where subject or object is in the given entity set."""
        entity_set = set(entities)
        return [t for t in self.triplets
                if t.subject in entity_set or t.object in entity_set]

    def get_triplets_in_window(self, t_start: float, t_end: float) -> list[Triplet]:
        """Return triplets whose time interval overlaps [t_start, t_end]."""
        return [t for t in self.triplets
                if t.t_end >= t_start and t.t_start <= t_end]

    def search(self, keywords: list[str]) -> list[Triplet]:
        """Keyword search over entity names and relation labels (case-insensitive)."""
        kws = [k.lower() for k in keywords]
        results = []
        for t in self.triplets:
            haystack = f"{t.subject} {t.relation} {t.object}".lower()
            if any(k in haystack for k in kws):
                results.append(t)
        return results

    # ── serialization ─────────────────────────────────────────────────────────

    def to_text(self, max_triplets: int | None = None) -> str:
        """Serialize to LLM-readable text."""
        if max_triplets is None:
            try:
                from src.config import get_settings
                max_triplets = get_settings().scene_graph.max_display_triplets
            except Exception:
                max_triplets = 50
        if not self.triplets:
            return "Scene graph is empty."
        lines = [f"Scene Graph ({len(self.triplets)} triplets, {len(self.entities)} entities):"]
        for i, t in enumerate(self.triplets[:max_triplets]):
            lines.append(f"  [{i + 1:2d}] {t.to_text()}  conf={t.confidence:.2f} src={t.source}")
        if len(self.triplets) > max_triplets:
            lines.append(f"  ... {len(self.triplets) - max_triplets} more triplets not shown")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "entities": {
                name: {
                    "type": e.entity_type,
                    "attributes": e.attributes,
                    "first_seen": e.first_seen,
                    "last_seen": e.last_seen,
                }
                for name, e in self.entities.items()
            },
            "triplets": [
                {
                    "subject": t.subject,
                    "relation": t.relation,
                    "object": t.object,
                    "t_start": t.t_start,
                    "t_end": t.t_end,
                    "confidence": t.confidence,
                    "source": t.source,
                }
                for t in self.triplets
            ],
        }

    # ── dunder ────────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.triplets)

    def __repr__(self) -> str:
        return f"SceneGraph(entities={len(self.entities)}, triplets={len(self.triplets)})"
