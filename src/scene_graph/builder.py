"""
SceneGraphBuilder: real VLM-based scene graph construction.

Processes a batch of video frames, calls the VLM with a structured
Chinese prompt, parses the JSON response, and merges discoveries into
the session's scene graph.

Entry point:
    build_frames(session, frame_ids, focus_entities, vl_client, ...)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.scene_graph.relation_vocab import RELATION_VOCAB

if TYPE_CHECKING:
    from src.memory.session import FrameMeta, VideoSession
    from src.perception.vl_client import VLClient

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "你是专业的视频内容理解专家。请仔细分析给定的视频帧序列，"
    "识别所有实体和实体间关系，以指定 JSON 格式输出场景图。"
    "只输出 JSON，不要添加任何解释文字。"
)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    timestamps: list[float],
    focus_entities: list[str],
    relation_vocab: list[str],
) -> str:
    ts_str = ", ".join(f"{t:.1f}s" for t in timestamps)
    focus_hint = (
        f"\n【重点关注】以下实体: {', '.join(focus_entities)}\n"
        if focus_entities else ""
    )
    # Show full vocab; take up to 50 terms
    vocab_str = "、".join(relation_vocab[:50])

    return f"""请分析上方 {len(timestamps)} 帧视频画面（时间戳: {ts_str}）。{focus_hint}
识别所有可见的人物（person）、物体（object）、场所（place）及其他实体（other），
以及实体之间的关系。

【关系词表】请严格从以下词汇中选择关系标签，禁止自造词汇：
{vocab_str}

【输出格式】严格 JSON，schema 如下：
{{
  "entities": [
    {{
      "id": "person_1",
      "type": "person",
      "label": "简短中文描述（如：红衣女性）",
      "attributes": {{"clothing": "红色外套", "action": "行走"}},
      "first_seen": 时间戳秒数,
      "last_seen": 时间戳秒数
    }}
  ],
  "relations": [
    {{
      "subject": "person_1",
      "relation": "骑乘",
      "object": "bicycle_1",
      "t_start": 开始时间戳,
      "t_end": 结束时间戳,
      "confidence": 0.85
    }}
  ]
}}

注意：
1. 同一个实体在不同帧应使用相同 id
2. id 格式：类型_序号，如 person_1、object_2
3. first_seen / last_seen 填入该实体在画面中第一次/最后一次出现的时间戳
4. confidence 表示你对该关系的确信度（0.0–1.0）
5. 若画面中没有明显实体或关系，返回空列表"""


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_vlm_output(text: str) -> Optional[dict]:
    """Parse VLM JSON output. Returns None if parsing fails."""
    import json

    text = text.strip()
    # Direct parse (response_format=json_object returns clean JSON)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    logger.warning("Failed to parse VLM output as JSON: %s", text[:200])
    return None


# ── Entity deduplication ──────────────────────────────────────────────────────

def _dedup_entities(entities: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """
    Deduplicate entities by (label, type). Merges attributes.

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
                # gap between the two windows
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
    max_retries: int = 2,
) -> Optional[dict]:
    """
    Call VLM on a batch of frames. Returns parsed JSON dict or None on failure.
    """
    image_paths = [f.path for f in frames if f.path and Path(f.path).exists()]
    if not image_paths:
        return None

    timestamps = [f.timestamp for f in frames]
    prompt = _build_prompt(timestamps, focus_entities, RELATION_VOCAB)

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
) -> dict:
    """
    Build / update the scene graph from a list of frame IDs.

    1. Fetch frames from session cache; skip missing paths.
    2. Split into batches of `batch_size` frames sorted by timestamp.
    3. For each batch, call VLM, parse response, deduplicate entities & merge relations.
    4. Filter by confidence threshold.
    5. Merge results into session.scene_graph.

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

    # Collect across batches
    all_entities: list[dict] = []
    all_relations: list[dict] = []
    batches_ok = batches_fail = 0

    for i in range(0, len(frames), batch_size):
        batch = frames[i: i + batch_size]
        parsed = _call_vlm_batch(vl_client, batch, focus_entities)
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

    # Deduplicate entities
    unique_entities, id_remap = _dedup_entities(all_entities)

    # Remap relation subject/object IDs
    for rel in all_relations:
        rel["subject"] = id_remap.get(rel.get("subject", ""), rel.get("subject", ""))
        rel["object"] = id_remap.get(rel.get("object", ""), rel.get("object", ""))

    # Apply focus filter (post-processing guard in addition to prompt hint)
    if focus_entities:
        focus_lower = {f.lower() for f in focus_entities}
        relevant_ids = {
            e["id"] for e in unique_entities
            if any(f in e["label"].lower() for f in focus_lower)
        }
        if relevant_ids:  # only filter if focus produces any results
            unique_entities = [e for e in unique_entities if e["id"] in relevant_ids]
            all_relations = [
                r for r in all_relations
                if r.get("subject") in relevant_ids or r.get("object") in relevant_ids
            ]

    # Merge relations across batches
    merged_relations = _merge_relations(all_relations, merge_window_sec)

    # Confidence threshold
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
