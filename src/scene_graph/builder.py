"""
SceneGraphBuilder: real VLM-based scene graph construction.

Processes a batch of video frames, calls the VLM with a structured
Chinese prompt, parses the JSON response, and merges discoveries into
the session's scene graph.

Entry point:
    build_frames(session, frame_ids, focus_entities, vl_client, ...)

v2 improvements:
  - Existing entities injected into VLM prompt to stabilize cross-batch naming
  - Post-processing cross-batch dedup via difflib string similarity
  - Parallel VLM batch calls via ThreadPoolExecutor + tqdm progress bar
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.scene_graph.relation_vocab import RELATION_VOCAB

if TYPE_CHECKING:
    from src.memory.session import FrameMeta, VideoSession
    from src.perception.vl_client import VLClient
    from src.scene_graph.graph import Entity

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an expert in video content understanding. Carefully analyze the "
    "given sequence of video frames, identify all entities and the relations "
    "between them, and output a scene graph in the specified JSON format. "
    "Output only JSON, with no explanatory text."
)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _format_existing_entities(existing: dict[str, "Entity"]) -> str:
    """Format existing graph entities for prompt context (max 20 shown)."""
    if not existing:
        return ""
    items = list(existing.items())[:20]
    lines = [f"  - {name} ({e.entity_type})" for name, e in items]
    extra = f"\n  ... ({len(existing)} total)" if len(existing) > 20 else ""
    return "\n".join(lines) + extra


def _build_prompt(
    timestamps: list[float],
    focus_entities: list[str],
    relation_vocab: list[str],
    existing_entities: dict[str, "Entity"] | None = None,
) -> str:
    ts_str = ", ".join(f"{t:.1f}s" for t in timestamps)
    focus_hint = (
        f"\n[Focus] Pay special attention to these entities: {', '.join(focus_entities)}\n"
        if focus_entities else ""
    )
    vocab_str = ", ".join(relation_vocab[:50])

    existing_hint = ""
    if existing_entities:
        existing_hint = (
            f"\n[Known entities] The following entities have already been found in "
            f"this video. If you detect the same or a highly similar entity, reuse "
            f"the exact same name in the label field — do not rename it:\n"
            f"{_format_existing_entities(existing_entities)}\n"
        )

    return f"""Analyze the {len(timestamps)} video frames above (timestamps: {ts_str}).{focus_hint}{existing_hint}
Identify all visible entities (person, object, place) and the relations between them.

[Relation vocabulary] Choose relation labels ONLY from the following list; do not invent new ones:
{vocab_str}

[Output format] Output ONLY JSON with the following structure, no extra fields or commentary:
{{
  "entities": [
    {{
      "id": "person_1",
      "type": "person|object|place",
      "label": "short English description",
      "attributes": {{"key": "value"}},
      "first_seen": {ts_str.split(',')[0].strip().rstrip('s')},
      "last_seen": {ts_str.split(',')[0].strip().rstrip('s')}
    }}
  ],
  "relations": [
    {{
      "subject": "person_1",
      "relation": "riding",
      "object": "bicycle_1",
      "t_start": {ts_str.split(',')[0].strip().rstrip('s')},
      "t_end": {ts_str.split(',')[0].strip().rstrip('s')},
      "confidence": 0.85
    }}
  ]
}}

Rules:
1. Use the same id for the same entity across frames; id format: type_index, e.g. person_1
2. confidence is a float in 0.0-1.0
3. If there are no entities or relations, use an empty list []
4. Output only JSON, with no prefix or suffix text"""


# ── Parsing ───────────────────────────────────────────────────────────────────

def _extract_json_array(text: str, key: str) -> Optional[list]:
    """
    Extract the first JSON array value for a given key from potentially
    malformed JSON text, using bracket-depth matching.

    Handles the case where the VLM emits duplicate keys or never closes
    the outer object — we just grab the first occurrence of each key's array.
    """
    import json
    import re

    pattern = rf'"{re.escape(key)}"\s*:\s*(\[)'
    m = re.search(pattern, text)
    if not m:
        return None
    start = m.start(1)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start: i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _parse_vlm_output(text: str) -> Optional[dict]:
    """
    Parse VLM JSON output with three fallback levels:
      1. Direct json.loads (clean JSON / json_object mode)
      2. Extract first { ... last } substring
      3. Array-level extraction for "entities" and "relations" keys
         (handles duplicate-key / unclosed-brace hallucinations)
    Returns None only if entities cannot be extracted at all.
    """
    import json

    text = text.strip()

    # Level 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Level 2: first { … last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(text[start: end + 1])
        except json.JSONDecodeError:
            pass

    # Level 3: bracket-depth array extraction (tolerates duplicate keys /
    # unclosed outer braces — a known Qwen-VL hallucination pattern)
    entities = _extract_json_array(text, "entities")
    if entities is not None:
        relations = _extract_json_array(text, "relations") or []
        logger.debug(
            "Level-3 array extraction: %d entities, %d relations",
            len(entities), len(relations),
        )
        return {"entities": entities, "relations": relations}

    logger.warning("Failed to parse VLM output as JSON: %s", text[:200])
    return None


# ── Entity deduplication ──────────────────────────────────────────────────────

def _dedup_entities(entities: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """
    Deduplicate entities by (label, type) within a single batch. Merges attributes.

    Returns
    -------
    (unique_entities, id_remap)
        id_remap maps each original id → canonical id (for relation relabelling).
    """
    canonical: dict[tuple, dict] = {}  # (label, type) → entity
    id_remap: dict[str, str] = {}

    for ent in entities:
        label = (ent.get("label") or ent.get("id", "")).strip()
        etype = ent.get("type", "object")
        key = (label.lower(), etype)
        eid = ent.get("id", label)

        if key in canonical:
            existing = canonical[key]
            existing["attributes"].update(ent.get("attributes") or {})
            fs = ent.get("first_seen", 0.0) or 0.0
            ls = ent.get("last_seen", 0.0) or 0.0
            if fs and (existing["first_seen"] == 0.0 or fs < existing["first_seen"]):
                existing["first_seen"] = fs
            if ls > existing["last_seen"]:
                existing["last_seen"] = ls
            id_remap[eid] = existing["id"]
        else:
            new_ent = {
                "id":         eid,
                "type":       etype,
                "label":      label,
                "attributes": dict(ent.get("attributes") or {}),
                "first_seen": float(ent.get("first_seen") or 0.0),
                "last_seen":  float(ent.get("last_seen") or 0.0),
            }
            canonical[key] = new_ent
            id_remap[eid] = eid

    return list(canonical.values()), id_remap


# ── Cross-batch entity deduplication against existing graph ───────────────────

def _cross_dedup_with_graph(
    new_entities: list[dict],
    existing: dict[str, "Entity"],
    threshold: float = 0.85,
) -> tuple[list[dict], dict[str, str]]:
    """
    Merge new entities into existing graph entities when their labels are
    sufficiently similar (SequenceMatcher ratio ≥ threshold, same type).

    Returns
    -------
    (truly_new, label_remap)
        truly_new  — new entities that do NOT match any existing entity
        label_remap — maps new entity label → existing canonical label
                      (for relation subject/object remapping)
    """
    truly_new: list[dict] = []
    label_remap: dict[str, str] = {}

    for ent in new_entities:
        new_label = ent.get("label", "")
        new_type = ent.get("type", "object")
        merged = False

        for existing_name, existing_ent in existing.items():
            if existing_ent.entity_type != new_type:
                continue
            ratio = SequenceMatcher(
                None, new_label.lower(), existing_name.lower()
            ).ratio()
            if ratio >= threshold:
                label_remap[new_label] = existing_name
                # Update existing entity's time range if new info is wider
                fs = ent.get("first_seen") or 0.0
                ls = ent.get("last_seen") or 0.0
                if fs and (existing_ent.first_seen == 0.0 or fs < existing_ent.first_seen):
                    existing_ent.first_seen = fs
                if ls > existing_ent.last_seen:
                    existing_ent.last_seen = ls
                existing_ent.attributes.update(ent.get("attributes") or {})
                merged = True
                logger.debug(
                    "Cross-batch merge: '%s' → '%s' (ratio=%.2f)",
                    new_label, existing_name, ratio,
                )
                break

        if not merged:
            truly_new.append(ent)

    return truly_new, label_remap


# ── Relation merging ──────────────────────────────────────────────────────────

def _merge_relations(
    relations: list[dict],
    merge_window_sec: float,
) -> list[dict]:
    """
    Merge relations with the same (subject, relation, object) triple
    whose time windows are adjacent or overlapping (gap ≤ merge_window_sec).

    t_start / t_end are expanded to the union; confidence takes the max.
    """
    merged: list[dict] = []

    for rel in relations:
        subj = rel.get("subject", "")
        verb = rel.get("relation", "")
        obj = rel.get("object", "")
        t0 = float(rel.get("t_start", 0.0) or 0.0)
        t1 = float(rel.get("t_end", t0) or t0)
        conf = float(rel.get("confidence", 0.75) or 0.75)

        key = (subj, verb, obj)
        found = False
        for ex in merged:
            if (ex["subject"], ex["relation"], ex["object"]) == key:
                gap = max(t0, ex["t_start"]) - min(t1, ex["t_end"])
                if gap <= merge_window_sec:
                    ex["t_start"] = min(ex["t_start"], t0)
                    ex["t_end"] = max(ex["t_end"], t1)
                    ex["confidence"] = max(ex["confidence"], conf)
                    found = True
                    break
        if not found:
            merged.append({
                "subject":    subj,
                "relation":   verb,
                "object":     obj,
                "t_start":    t0,
                "t_end":      t1,
                "confidence": conf,
            })

    return merged


# ── VLM call with retry ───────────────────────────────────────────────────────

def _call_vlm_batch(
    vl_client: "VLClient",
    frames: list["FrameMeta"],
    focus_entities: list[str],
    existing_entities: dict[str, "Entity"] | None = None,
    max_retries: int = 2,
) -> Optional[dict]:
    """
    Call VLM on a batch of frames. Returns parsed JSON dict or None on failure.
    """
    image_paths = [f.path for f in frames if f.path and Path(f.path).exists()]
    if not image_paths:
        return None

    timestamps = [f.timestamp for f in frames]
    prompt = _build_prompt(timestamps, focus_entities, RELATION_VOCAB, existing_entities)

    for attempt in range(max_retries):
        try:
            raw = vl_client.call_multi(image_paths, prompt, _SYSTEM_PROMPT)
            parsed = _parse_vlm_output(raw)
            if parsed is not None:
                return parsed
            logger.warning("VLM output parse failed (attempt %d/%d)", attempt + 1, max_retries)
        except Exception as exc:
            logger.warning("VLM call failed (attempt %d/%d): %s", attempt + 1, max_retries, exc)

    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def build_frames(
    session: "VideoSession",
    frame_ids: list[str],
    focus_entities: list[str],
    vl_client: "VLClient",
    merge_window_sec: float = 3.0,
    confidence_threshold: float = 0.75,
    batch_size: int = 4,
    max_parallel_batches: int = 3,
    cross_dedup_threshold: float = 0.85,
) -> dict:
    """
    Build / update the scene graph from a list of frame IDs.

    1. Fetch frames from session cache; skip missing paths.
    2. Split into batches of `batch_size` frames sorted by timestamp.
    3. Call VLM on all batches in parallel (up to `max_parallel_batches` threads).
    4. For each batch: parse response, deduplicate entities, merge relations.
    5. Cross-batch dedup against existing graph entities (difflib similarity).
    6. Filter by confidence threshold.
    7. Merge results into session.scene_graph.

    Returns
    -------
    {
        "new_entities":  list[str]   entity labels added
        "new_relations": list[dict]  {subject, relation, object}
        "nodes_added":   int
        "edges_added":   int
        "batches_ok":    int         batches that succeeded
        "batches_fail":  int         batches that failed
    }
    """
    try:
        from tqdm import tqdm as _tqdm
        _has_tqdm = True
    except ImportError:
        _has_tqdm = False

    # Resolve and sort frames
    frames = [session.get_frame(fid) for fid in frame_ids]
    frames = [
        f for f in frames
        if f is not None and f.path and Path(f.path).exists()
    ]
    if not frames:
        logger.warning("build_frames: no frames with valid paths found in %s", frame_ids)
        return {
            "new_entities":  [],
            "new_relations": [],
            "nodes_added":   0,
            "edges_added":   0,
            "batches_ok":    0,
            "batches_fail":  0,
        }

    frames.sort(key=lambda f: f.timestamp)

    # Snapshot existing graph entities for prompt context + cross-dedup
    existing_entities = dict(session.scene_graph.entities)

    # Split into batches
    batches = [frames[i: i + batch_size] for i in range(0, len(frames), batch_size)]
    n_batches = len(batches)

    all_entities: list[dict] = []
    all_relations: list[dict] = []
    batches_ok = batches_fail = 0

    # ── Parallel VLM calls ────────────────────────────────────────────────────
    results: list[Optional[dict]] = [None] * n_batches

    with ThreadPoolExecutor(max_workers=max_parallel_batches) as executor:
        future_to_idx = {
            executor.submit(
                _call_vlm_batch,
                vl_client,
                batch,
                focus_entities,
                existing_entities,
            ): idx
            for idx, batch in enumerate(batches)
        }

        if _has_tqdm:
            from tqdm import tqdm
            pbar = tqdm(total=n_batches, desc="Building scene graph", unit="batch")
        else:
            pbar = None

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                logger.warning("Batch %d raised exception: %s", idx, exc)
                results[idx] = None
            if pbar:
                pbar.update(1)

        if pbar:
            pbar.close()

    for parsed in results:
        if parsed is None:
            batches_fail += 1
            continue
        batches_ok += 1
        all_entities.extend(parsed.get("entities") or [])
        all_relations.extend(parsed.get("relations") or [])

    if not all_entities and not all_relations:
        return {
            "new_entities":  [],
            "new_relations": [],
            "nodes_added":   0,
            "edges_added":   0,
            "batches_ok":    batches_ok,
            "batches_fail":  batches_fail,
        }

    # ── Within-batch entity deduplication ─────────────────────────────────────
    unique_entities, id_remap = _dedup_entities(all_entities)

    # Remap relation subject/object IDs
    for rel in all_relations:
        rel["subject"] = id_remap.get(rel.get("subject", ""), rel.get("subject", ""))
        rel["object"] = id_remap.get(rel.get("object", ""), rel.get("object", ""))

    # ── Cross-batch dedup against existing graph ──────────────────────────────
    truly_new, label_remap = _cross_dedup_with_graph(
        unique_entities, existing_entities, threshold=cross_dedup_threshold
    )

    # Apply label remap to relations (subject/object may now point to existing names)
    for rel in all_relations:
        rel["subject"] = label_remap.get(rel["subject"], rel["subject"])
        rel["object"] = label_remap.get(rel["object"], rel["object"])

    # Replace unique_entities with only the truly new ones
    unique_entities = truly_new

    # ── Focus filter ──────────────────────────────────────────────────────────
    if focus_entities:
        focus_lower = {f.lower() for f in focus_entities}
        relevant_ids = {
            e["id"] for e in unique_entities
            if any(f in e["label"].lower() for f in focus_lower)
        }
        if relevant_ids:
            unique_entities = [e for e in unique_entities if e["id"] in relevant_ids]
            all_relations = [
                r for r in all_relations
                if r.get("subject") in relevant_ids or r.get("object") in relevant_ids
            ]

    # ── Merge and filter relations ─────────────────────────────────────────────
    merged_relations = _merge_relations(all_relations, merge_window_sec)
    merged_relations = [
        r for r in merged_relations
        if r.get("confidence", 1.0) >= confidence_threshold
    ]

    # Build entity label ↔ id mapping for edge resolution
    id_to_label = {e["id"]: e["label"] for e in unique_entities}

    # Prepare session update
    new_nodes = [
        {
            "name":       e["label"],
            "type":       e.get("type", "object"),
            "attributes": e.get("attributes", {}),
            "first_seen": e.get("first_seen", 0.0),
            "last_seen":  e.get("last_seen", 0.0),
        }
        for e in unique_entities
        if e.get("label")
    ]

    new_edges = [
        {
            "subject":    id_to_label.get(r["subject"], r["subject"]),
            "relation":   r["relation"],
            "object":     id_to_label.get(r["object"], r["object"]),
            "t_start":    r["t_start"],
            "t_end":      r["t_end"] if r["t_end"] > r["t_start"] else r["t_start"] + merge_window_sec,
            "confidence": r["confidence"],
            "source":     "vlm",
        }
        for r in merged_relations
        if r.get("subject") and r.get("object") and r.get("relation")
    ]

    stats = session.update_scene_graph(new_nodes, new_edges)

    return {
        "new_entities":  [e["label"] for e in unique_entities],
        "new_relations": [
            {
                "subject":  id_to_label.get(r["subject"], r["subject"]),
                "relation": r["relation"],
                "object":   id_to_label.get(r["object"], r["object"]),
            }
            for r in merged_relations
        ],
        "nodes_added":   stats["nodes_added"],
        "edges_added":   stats["edges_added"],
        "batches_ok":    batches_ok,
        "batches_fail":  batches_fail,
    }
