"""
English scene graph retriever with multi-strategy matching.

Strategy order (first hit wins for each triplet; scores accumulate):
  a. Exact entity name match  — query token equals an entity name
  b. Relation verb match      — query token is in RELATION_VOCAB
  c. Multi-token substring OR scoring — token found inside subject/relation/object
  d. Time constraint filter   — restrict to triplets in a time window if the query
                                 contains temporal keywords ("beginning", "last", …)

Usage::

    result = retrieve_triplets(question, session.scene_graph, top_k=5)
    # result.keys() = ["triplets", "entity_summary", "found",
    #                  "matched_tokens", "nearby_entities"]
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.scene_graph.graph import SceneGraph, Triplet

logger = logging.getLogger(__name__)


# ── Lemmatizer (lazy, graceful fallback to a light suffix stemmer) ────────────
_lemmatizer = None
_lemmatizer_ready = False


def _get_lemmatizer():
    """Return an nltk WordNetLemmatizer if available, else None (offline-safe)."""
    global _lemmatizer, _lemmatizer_ready
    if _lemmatizer_ready:
        return _lemmatizer
    _lemmatizer_ready = True
    try:
        import nltk
        from nltk.stem import WordNetLemmatizer

        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        _lemmatizer = WordNetLemmatizer()
    except Exception as exc:  # nltk missing or download failed → fallback stemmer
        logger.debug("nltk lemmatizer unavailable (%s); using suffix stemmer", exc)
        _lemmatizer = None
    return _lemmatizer


def _lemmatize(token: str) -> str:
    """Normalize a token toward its base form (verb-first, then noun)."""
    lz = _get_lemmatizer()
    if lz is not None:
        verb = lz.lemmatize(token, pos="v")
        if verb != token:
            return verb
        return lz.lemmatize(token, pos="n")
    # Lightweight fallback: strip common inflectional suffixes
    for suf in ("ing", "ed", "es", "s"):
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            return token[: -len(suf)]
    return token


# ── Backward-compat no-op (English needs no jieba user dictionary) ────────────

_registered_words: set[str] = set()


def register_domain_words(words: list[str]) -> None:
    """No-op kept for API compatibility (the Chinese pipeline used jieba here)."""
    for w in words:
        if w:
            _registered_words.add(w)


# ── Tokenization ──────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str, extra_words: list[str] | None = None) -> list[str]:
    """
    Tokenize *text*: lowercase, split on non-alphanumeric runs, drop stopwords,
    and lemmatize each remaining token toward its base form.

    `extra_words` (entity names / relation verbs) is accepted for API
    compatibility but not needed for English whitespace tokenization.
    """
    from src.scene_graph.stopwords import STOPWORDS

    if extra_words:
        register_domain_words(extra_words)

    raw_tokens = _TOKEN_RE.findall(text.lower())
    tokens = [
        _lemmatize(t)
        for t in raw_tokens
        if t and t not in STOPWORDS
    ]
    # Filter stopwords again post-lemmatization (e.g. "does" → "doe" is harmless,
    # but a lemma may land back on a stopword) and drop empties.
    return [t for t in tokens if t and t not in STOPWORDS]


# ── Time window extraction ────────────────────────────────────────────────────

def _extract_time_constraint(
    tokens: list[str],
    video_duration: float = 0.0,
) -> tuple[float, float] | None:
    """
    Return (t_start, t_end) window if query tokens contain temporal keywords,
    else None.

    "beginning"/"first" → first 20 % of video; "last"/"end" → last 20 %.
    A bare number token is treated as an explicit timestamp (seconds, or
    minutes when a minute-unit token is also present).
    """
    from src.scene_graph.stopwords import TIME_KEYWORDS

    # Prefix-stem match so detection survives lemmatization/stemming
    # (e.g. "beginning" → "beginn" still matches the "begin" keyword).
    positions: dict[str, str] = {}
    for tok in tokens:
        for kw, tag in TIME_KEYWORDS.items():
            if tok == kw or tok.startswith(kw):
                positions[tok] = tag
                break

    # Explicit numeric timestamp like "30" (seconds) or "2" + "minutes"
    is_minutes = any(t in ("minute", "minutes", "min") for t in tokens)
    for tok in tokens:
        if tok.isdigit():
            sec = float(tok) * (60.0 if is_minutes else 1.0)
            pad = 5.0 if is_minutes else 3.0
            return (max(0.0, sec - pad), sec + pad)

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
    question        : Natural-language English query.
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

    # Register domain words (no-op for English; preserved for API parity)
    extra_words = RELATION_VOCAB + entity_names
    tokens = tokenize(question, extra_words=extra_words)

    if not tokens:
        tokens = [question.strip().lower()] if question.strip() else []

    query_token_set = set(tokens)

    # ── a. Exact entity name match ─────────────────────────────────────────────
    exact_entity_hits: set[str] = {
        name for name in entity_names if name.lower() in query_token_set
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
