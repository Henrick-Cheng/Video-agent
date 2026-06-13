"""
Build a stratified MMBench-Video benchmark subset in this repo's format.

Source: HF dataset `opencompass/MMBench-Video` (NeurIPS 2024 D&B,
arXiv 2406.14515) — ~609 YouTube videos (30s-6min), 1998 free-form QA pairs,
26 leaf capabilities under 9 second-level dimensions. Videos ship inside the
repo as pickle chunks; `unwrap_videos` restores them to mp4 (official recipe
from the dataset README).

Sampling protocol (disclosed in the thesis):
  - Each question is assigned a PRIMARY L2 dimension = the L2 of its first
    listed leaf dimension (questions are multi-label; official aggregation
    still counts a question in every L2 it touches — see MMV_DIMENSIONS).
  - Per-L2 quotas (total 150) oversample TR (temporal) and HL (hallucination),
    the dimensions where the scene-graph agent's design predicts an edge.
  - Within each L2, questions are spread across 3 video-duration buckets
    (<90s / 90-180s / >180s) round-robin, fixed seed, no replacement.
  - Shortfalls (an L2 × bucket cell with too few questions) backfill first
    from the same L2's other buckets, then from the global remainder.

Usage:
    python3 -m src.eval.build_mmbench_video \
        --out benchmarks/mmbv_150.json --total 150 --seed 42
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pickle
import random
from collections import defaultdict
from pathlib import Path

# ── Official dimension taxonomy (verbatim from VLMEvalKit utils) ──────────────

MMV_DIMENSIONS = {
    "CP": ["Video Topic", "Video Emotion", "Video Scene", "Video Style"],
    "FP-S": ["OCR", "Object Recognition", "Attribute Recognition",
             "Event Recognition", "Human Motion", "Counting"],
    "FP-C": ["Spatial Relationship", "Human-object Interaction", "Human Interaction"],
    "HL": ["Hallucination"],
    "LR": ["Structuralized Image-Text Understanding", "Mathematical Calculation"],
    "AR": ["Physical Property", "Function Reasoning", "Identity Reasoning"],
    "RR": ["Natural Relation", "Physical Relation", "Social Relation"],
    "CSR": ["Common Sense Reasoning"],
    "TR": ["Counterfactual Reasoning", "Causal Reasoning", "Future Prediction"],
}
LEAF_TO_L2 = {leaf: l2 for l2, leaves in MMV_DIMENSIONS.items() for leaf in leaves}

# Per-L2 question quotas (sum = 150). TR/HL oversampled relative to the
# source distribution (242 / 62 of 1998) because they probe the agent's
# design hypotheses; the rest roughly track availability.
QUOTAS = {
    "TR": 30, "HL": 15, "FP-S": 25, "CP": 15, "FP-C": 15,
    "AR": 14, "RR": 14, "CSR": 12, "LR": 10,
}

DURATION_BUCKETS = ((0, 90), (90, 180), (180, 10 ** 9))
BUCKET_LABELS = ("<90s", "90-180s", ">180s")


# ── HF data access ────────────────────────────────────────────────────────────

def snapshot_dir() -> Path:
    from huggingface_hub import snapshot_download
    return Path(snapshot_download("opencompass/MMBench-Video", repo_type="dataset"))


def unwrap_videos(root: Path) -> Path:
    """Restore mp4 files from the pkl chunks (official dataset README recipe)."""
    base_dir = root / "video_pkl"
    target_dir = root / "video"
    if target_dir.exists() and any(target_dir.iterdir()):
        print(f"[unwrap] videos already restored at {target_dir}")
        return target_dir

    target_dir.mkdir(exist_ok=True)
    for pkl_file in sorted(base_dir.iterdir()):
        print(f"[unwrap] {pkl_file.name} ...")
        with open(pkl_file, "rb") as fh:
            video_data = pickle.load(fh)
        for video_name, video_content in video_data.items():
            out = target_dir / f"{video_name}.mp4"
            if not out.exists():
                out.write_bytes(video_content)
    n = sum(1 for _ in target_dir.iterdir())
    print(f"[unwrap] restored {n} videos to {target_dir}")
    return target_dir


def video_duration_sec(path: Path) -> float:
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        return n / fps if fps > 0 else 0.0
    finally:
        cap.release()


def bucket_of(duration: float) -> int:
    for i, (lo, hi) in enumerate(DURATION_BUCKETS):
        if lo <= duration < hi:
            return i
    return len(DURATION_BUCKETS) - 1


# ── Sampling ──────────────────────────────────────────────────────────────────

def stratified_sample(rows: list[dict], total: int, seed: int) -> list[dict]:
    """Quota-per-L2, round-robin over duration buckets, fixed seed."""
    rng = random.Random(seed)

    # Scale quotas if a non-default total is requested.
    scale = total / sum(QUOTAS.values())
    quotas = {l2: max(1, round(q * scale)) for l2, q in QUOTAS.items()}

    pools: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        pools[r["l2"]][r["bucket"]].append(r)
    for l2 in pools:
        for b in pools[l2]:
            rng.shuffle(pools[l2][b])

    picked: list[dict] = []
    picked_ids: set = set()
    leftovers: list[dict] = []

    for l2, quota in quotas.items():
        cells = [pools[l2][b] for b in range(len(DURATION_BUCKETS))]
        got: list[dict] = []
        # Round-robin across buckets until quota or all cells empty.
        while len(got) < quota and any(cells):
            for cell in cells:
                if len(got) >= quota:
                    break
                while cell:
                    cand = cell.pop()
                    if cand["index"] not in picked_ids:
                        got.append(cand)
                        picked_ids.add(cand["index"])
                        break
        picked.extend(got)
        if len(got) < quota:
            print(f"[sample] WARN {l2}: wanted {quota}, got {len(got)} (pool exhausted)")
        for cell in cells:
            leftovers.extend(cell)

    # Backfill from the global remainder if any quota fell short.
    rng.shuffle(leftovers)
    while len(picked) < total and leftovers:
        cand = leftovers.pop()
        if cand["index"] not in picked_ids:
            picked.append(cand)
            picked_ids.add(cand["index"])

    return picked


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    import pandas as pd

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="benchmarks/mmbv_150.json")
    ap.add_argument("--total", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = snapshot_dir()
    video_dir = unwrap_videos(root)
    df = pd.read_csv(root / "MMBench-Video.tsv", sep="\t")
    print(f"[load] {len(df)} questions, {df['video'].nunique()} videos")

    print("[duration] probing video durations ...")
    durations: dict[str, float] = {}
    for vid in df["video"].unique():
        p = video_dir / f"{vid}.mp4"
        durations[vid] = video_duration_sec(p) if p.exists() else 0.0
    missing = [v for v, d in durations.items() if d <= 0]
    if missing:
        print(f"[duration] WARN {len(missing)} videos missing/unreadable; "
              f"their questions are excluded")

    rows = []
    for _, r in df.iterrows():
        dur = durations.get(r["video"], 0.0)
        if dur <= 0:
            continue
        leaves = [x for x in ast.literal_eval(r["dimensions"]) if x in LEAF_TO_L2]
        if not leaves:
            continue
        rows.append({
            "index": int(r["index"]),
            "video": r["video"],
            "video_type": r["video_type"],
            "question": r["question"],
            "answer": r["answer"],
            "leaves": leaves,
            "l2": LEAF_TO_L2[leaves[0]],  # primary dimension (first leaf)
            "duration": dur,
            "bucket": bucket_of(dur),
        })

    picked = stratified_sample(rows, args.total, args.seed)

    # Repo benchmark format (consumed by src/eval/run_benchmark.py).
    bench = [
        {
            "id": f"mmbv-{r['index']:04d}",
            "video": str(video_dir / f"{r['video']}.mp4"),
            "category": r["l2"],
            "question": r["question"],
            "reference_answer": r["answer"],
            "key_facts": [],
            "_source": {
                "dataset": "MMBench-Video",
                "index": r["index"],
                "youtube_id": r["video"],
                "video_type": r["video_type"],
                "dimensions": r["leaves"],
                "duration_sec": round(r["duration"], 1),
                "duration_bucket": BUCKET_LABELS[r["bucket"]],
            },
        }
        for r in sorted(picked, key=lambda x: x["index"])
    ]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bench, ensure_ascii=False, indent=2), encoding="utf-8")

    # Sampling summary (goes into the thesis disclosure).
    from collections import Counter
    l2c = Counter(r["l2"] for r in picked)
    bc = Counter(BUCKET_LABELS[r["bucket"]] for r in picked)
    vids = len({r["video"] for r in picked})
    print(f"\n[done] {len(bench)} questions over {vids} videos → {out}")
    print(f"  L2:      {dict(sorted(l2c.items()))}")
    print(f"  buckets: {dict(sorted(bc.items()))}")
    print(f"  seed={args.seed}, quotas={QUOTAS}")


if __name__ == "__main__":
    main()
