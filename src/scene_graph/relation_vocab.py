"""
Closed-vocabulary relation labels for the Video Agent scene graph.

The VLM prompt instructs the model to select relations from this list,
which keeps the graph schema consistent and deduplication reliable.

50 verbs covering the most common human-object and person-person interactions
in real-world video (surveillance, daily activity, social scene, traffic, etc.).

Note: kept as a 1:1 English port of the original Chinese vocabulary so the
matching architecture is unchanged. A future step may align this set to the
Action Genome predicate vocabulary for better AGQA fidelity.
"""
from __future__ import annotations

RELATION_VOCAB: list[str] = [
    # ── holding / operating ────────────────────────────────────────────────
    "holding",        # holding (general possession)
    "carrying",       # carrying in hand
    "carrying_on",    # carrying on body / bag
    "using",          # using a tool / device
    "operating",      # operating a machine / panel

    # ── vision / attention ─────────────────────────────────────────────────
    "looking_at",     # looking at (direction)
    "gazing_at",      # gazing at (sustained attention)
    "watching",       # observing / watching carefully
    "pointing_at",    # pointing at

    # ── movement ───────────────────────────────────────────────────────────
    "walking_toward", # walking toward
    "running_toward", # running toward
    "approaching",    # approaching / getting closer
    "moving_away",    # moving away from
    "following",      # following
    "chasing",        # chasing
    "crossing",       # crossing / passing through
    "passing_by",     # passing by
    "entering",       # entering
    "leaving",        # leaving / exiting

    # ── interaction / social ───────────────────────────────────────────────
    "talking_to",     # talking / conversing with
    "giving",         # giving to
    "receiving",      # receiving from
    "cooperating",    # cooperating with
    "confronting",    # confronting / facing off
    "helping",        # helping
    "avoiding",       # avoiding / evading

    # ── force / contact ────────────────────────────────────────────────────
    "pushing_away",   # pushing away
    "pushing",        # pushing (object)
    "pulling",        # pulling
    "grabbing",       # grabbing / seizing
    "putting_down",   # putting down
    "lifting",        # lifting
    "touching",       # touching
    "blocking",       # blocking

    # ── posture / position ─────────────────────────────────────────────────
    "sitting_on",     # sitting on / in
    "standing_on",    # standing on / at
    "lying_on",       # lying on
    "leaning_on",     # leaning against
    "climbing",       # climbing

    # ── object manipulation ────────────────────────────────────────────────
    "opening",        # opening (door, box, etc.)
    "closing",        # closing
    "riding",         # riding (bicycle, horse, etc.)
    "driving",        # driving (vehicle)

    # ── spatial relations ──────────────────────────────────────────────────
    "located_at",     # located at / in
    "stopped_at",     # stopped at / parked at
    "facing",         # facing toward
    "facing_away",    # facing away from

    # ── object-to-object ───────────────────────────────────────────────────
    "placed_on",      # placed on / in
    "connected_to",   # connected to
    "belonging_to",   # belonging to / owned by
]

# Convenience set for O(1) membership test
RELATION_VOCAB_SET: frozenset[str] = frozenset(RELATION_VOCAB)


def is_valid_relation(rel: str) -> bool:
    """Return True if rel is in the closed vocabulary."""
    return rel in RELATION_VOCAB_SET
