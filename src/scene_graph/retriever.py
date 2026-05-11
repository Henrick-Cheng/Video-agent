"""
Chinese scene graph retriever with multi-strategy matching.

Strategy order (first hit wins for each triplet; scores accumulate):
  a. Exact entity name match  — query token equals an entity name
  b. Relation verb match      — query token is in RELATION_VOCAB
  c. Multi-token substring OR scoring — token found inside subject/relation/object
  d. Time constraint filter   — restrict to triplets in a time window if the query
                                 contains temporal keywords ("开头", "最后", …)

Usage::

    result = retrieve_triplets(question, session.scene_graph, top_k=5)
    # result.keys() = ["triplets", "entity_summary", "found",
    #                  "matched_tokens", "nearby_entities"]
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.scene_graph.graph import SceneGraph, Triplet

logger = logging.getLogger(__name__)

# ── Lazy jieba import (avoids slow startup for offline tests) ─────────────────
_jieba_ready = False


def _ensure_jieba() -> None:
    global _jieba_ready
    if _jieba_ready:
        return
    import jieba
    jieba.setLogLevel(logging.WARNING)
    _jieba_ready = True


# ── Dynamic user-dict injection ───────────────────────────────────────────────

_registered_words: set[str] = set()


def register_domain_words(words: list[str]) -> None:
    """Add relation verbs and entity names to jieba's custom dictionary."""
    import jieba
    _ensure_jieba()
    for w in words:
        if w and w not in _registered_words:
            jieba.add_word(w, freq=10000)
            _registered_words.add(w)


# ── Tokenization ──────────────────────────────────────────────────────────────

def tokenize(text: str, extra_words: list[str] | None = None) -> list[str]:
    """
    Segment *text* using jieba, remove stopwords, return meaningful tokens.

    Extra words (entity names, relation verbs) are registered into jieba's
    user dictionary so they are not split across characters.
    """
    import jieba
    from src.scene_graph.stopwords import STOPWORDS

    _ensure_jieba()
    if extra_words:
        register_domain_words(extra_words)

    raw_tokens = list(jieba.cut(text, cut_all=False))
    tokens = [
        t.strip()
        for t in raw_tokens
        if t.strip() and t.strip() not in STOPWORDS and len(t.strip()) > 0
    ]
    return tokens


# ── Time window extraction ────────────────────────────────────────────────────

def _extract_time_constraint(
    tokens: list[str],
    video_duration: float = 0.0,
) -> tuple[float, float] | None:
    """
    Return (t_start, t_end) window if query tokens contain temporal keywords,
    else None.

    "开头" → first 20 % of video; "最后" → last 20 %.
    """
    from src.scene_graph.stopwords import TIME_KEYWORDS
    import re

    positions = {t: TIME_KEYWORDS[t] for t in tokens if t in TIME_KEYWORDS}

    # Explicit seconds like "30秒" or "1分" in the original token list
    for tok in tokens:
        m = re.match(r"(\d+)\s*秒", tok)
        if m:
            sec = float(m.group(1))
            return (max(0.0, sec - 3.0), sec + 3.0)
        m = re.match(r"(\d+)\s*分", tok)
        if m:
            sec = float(m.group(1)) * 60
            return (max(0.0, sec - 5.0), sec + 5.0)

    if not positions:
        return None

    if "start" in positions.values():
        bound = video_duration * 0.2 if video_duration > 0 else 30.0
        return (0.0, bound)
    if "end" in positions.values():
        bound = video_duration * 0.8 if video_duration > 0 else 0.0
        return (bound, video_duration if video_duration > 0 else 1e9)
    return None


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _score_triplet(triplet: "Triplet", query_tokens: set[str]) -> float:
    """
    Score one triplet against a set of query tokens.

    Scoring weights:
      +2.0  token equals entity name (subject or object) — strong signal
      +1.5  token equals relation verb                   — medium signal
      +0.5  token is substring of subject/object/relation — weak signal
    """
    subj = triplet.subject.lower()
    rel = triplet.relation.lower()
    obj = triplet.object.lower()
    score = 0.0

    for tok in query_tokens:
        t = tok.lower()
        # Exact match
        if t == subj or t == obj:
            score += 2.0
        elif t == rel:
            score += 1.5
        # Substring match
        elif t in subj or t in obj:
            score += 0.5
        elif t in rel:
            score += 0.3

    return score


# ── Main entry point ──────────────────────────────────────────────────────────

def retrieve_triplets(
    question: str,
    graph: "SceneGraph",
    top_k: int = 5,
    video_duration: float = 0.0,
    min_score: float = 0.3,
) -> dict:
    """
    Retrieve scene graph triplets relevant to *question*.

    Parameters
    ----------
    question        : Natural-language Chinese query.
    graph           : The session's SceneGraph.
    top_k           : Maximum number of triplets to return.
    video_duration  : Used for time-window estimation (seconds).
    min_score       : Triplets scoring below this are excluded.

    Returns
    -------
    dict with keys:
      triplets        — list[dict] sorted by score descending (≤ top_k)
      entity_summary  — human-readable summary of all entities in graph
      found           — bool, True if at least one triplet returned
      matched_tokens  — list[str] tokens that produced ≥ 1 hit
      nearby_entities — list[str] close-match entities when found=False
    """
    from src.scene_graph.relation_vocab import RELATION_VOCAB

    entity_names = list(graph.entities.keys())
    entity_summary = (
        f"Entities ({len(entity_names)}): {', '.join(entity_names)}"
        if entity_names
        else "Scene graph is empty."
    )

    if not graph.triplets:
        return {
            "triplets": [],
            "entity_summary": entity_summary,
            "found": False,
            "matched_tokens": [],
            "nearby_entities": [],
        }

    # Register domain words so jieba doesn't split them
    extra_words = RELATION_VOCAB + entity_names
    tokens = tokenize(question, extra_words=extra_words)

    if not tokens:
        tokens = [question.strip()] if question.strip() else []

    query_token_set = set(tokens)

    # ── a. Exact entity name match ─────────────────────────────────────────────
    exact_entity_hits: set[str] = {
        name for name in entity_names if name in query_token_set
    }

    # ── b. Relation verb match ─────────────────────────────────────────────────
    relation_hits: set[str] = query_token_set & set(RELATION_VOCAB)

    # ── c. Score all triplets ──────────────────────────────────────────────────
    scored: list[tuple[float, "Triplet"]] = []
    for t in graph.triplets:
        score = _score_triplet(t, query_token_set)
        if score >= min_score:
            scored.append((score, t))

    # ── d. Time constraint filter ──────────────────────────────────────────────
    time_window = _extract_time_constraint(tokens, video_duration)
    if time_window is not None:
        t_lo, t_hi = time_window
        scored = [
            (s, t) for s, t in scored
            if t.t_end >= t_lo and t.t_start <= t_hi
        ]

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # Determine which tokens actually contributed to hits
    matched_tokens: list[str] = []
    for tok in tokens:
        tl = tok.lower()
        for _, t in top:
            subj = t.subject.lower()
            rel = t.relation.lower()
            obj = t.object.lower()
            if tl in subj or tl in obj or tl == rel or tl in rel:
                if tok not in matched_tokens:
                    matched_tokens.append(tok)
                break

    # ── Fallback: nearby entities when nothing matched ─────────────────────────
    nearby_entities: list[str] = []
    if not top:
        # Partial-match entity names against each query token
        for name in entity_names:
            name_l = name.lower()
            for tok in tokens:
                if tok.lower() in name_l or name_l in tok.lower():
                    if name not in nearby_entities:
                        nearby_entities.append(name)
                    break

    triplets_out = [
        {
            "subject":    t.subject,
            "relation":   t.relation,
            "object":     t.object,
            "t_start":    t.t_start,
            "t_end":      t.t_end,
            "confidence": t.confidence,
            "score":      round(s, 2),
        }
        for s, t in top
    ]

    return {
        "triplets":       triplets_out,
        "entity_summary": entity_summary,
        "found":          bool(triplets_out),
        "matched_tokens": matched_tokens,
        "nearby_entities": nearby_entities,
    }
