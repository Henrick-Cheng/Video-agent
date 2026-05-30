"""
build_agqa_benchmark.py — convert AGQA 2.0 question CSVs into the project's
Chinese benchmark JSON format.

AGQA questions are auto-generated from Charades videos' spatio-temporal scene
graphs (Action Genome). This script:
  1. Reads the AGQA CSV in chunks (the balanced split is multi-GB).
  2. Samples ~N videos × ~K questions each, balanced across AGQA categories.
  3. Translates English question + answer to Chinese (LLM, with a disk cache).
  4. Emits benchmarks/agqa_zh_small.json in the project schema:
        {id, video, question, reference_answer, category, key_facts}

The output `video` field points at data/videos/charades/<video_id>.mp4 — the raw
Charades videos must be downloaded separately (this repo / AGQA only ship HDF5
features, not videos). Run with --dry-run first to validate CSV parsing and see
the sampled video_id list (so you only download those videos).

Usage:
    # 1. inspect schema + sample, no translation, no API cost:
    python -m src.eval.build_agqa_benchmark --csv data/agqa/csvs --dry-run

    # 2. full build with Chinese translation:
    python -m src.eval.build_agqa_benchmark --csv data/agqa/csvs \\
        --num-videos 10 --per-video 7 --out benchmarks/agqa_zh_small.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Column auto-detection ───────────────────────────────────────────────────
# AGQA CSV column names are not 100% fixed across releases, so we detect by a
# list of likely candidates (case-insensitive). The first match wins. The exact
# detected mapping is printed on every run so it can be corrected if needed.
_COL_CANDIDATES = {
    "question": ["question", "q", "ques"],
    "answer":   ["answer", "ans", "a"],
    "video_id": ["video_id", "vid_id", "vidid", "video", "vid", "key_video"],
    "id":       ["key", "question_id", "qid", "id", "index"],
    # category-ish; we take the first that exists for the per-question category
    "category": ["global", "reasoning", "semantic", "category", "type",
                 "structural", "ans_type", "global1"],
    "ans_type": ["ans_type", "answer_type", "atype"],
}

_YES_NO_ZH = {"yes": "是", "no": "否"}


def _detect_columns(header: list[str]) -> dict[str, str | None]:
    lower = {h.lower(): h for h in header}
    mapping: dict[str, str | None] = {}
    for field, cands in _COL_CANDIDATES.items():
        mapping[field] = next((lower[c] for c in cands if c in lower), None)
    return mapping


def _norm_category(raw: str) -> str:
    """Collapse AGQA's (sometimes list-like) category string to one token."""
    if raw is None:
        return "general"
    s = str(raw).strip().strip("[]").strip("'\"")
    if not s:
        return "general"
    # list-like "['obj-rel', 'exists']" → first element
    for sep in (",", "|", ";", " "):
        if sep in s:
            s = s.split(sep)[0].strip().strip("'\"")
            break
    return s or "general"


_NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "once", "twice", "thrice",
}


def _infer_category(question: str, answer: str) -> str:
    """Heuristic category from question template + answer.

    The AGQA *balanced* CSVs ship no reasoning-type column (it lives in the JSON
    hierarchies, which we don't download), so we recover a coarse but objective
    axis from the question wording and the answer string. Order matters: more
    specific patterns are checked first.
    """
    q = (question or "").lower()
    a = (answer or "").strip().lower()
    if a in ("yes", "no"):
        return "binary"
    if any(k in q for k in ("how long", "longer", "shorter", "longest", "shortest")):
        return "duration"
    if "how many" in q or "number of" in q or a.isdigit() or a in _NUMBER_WORDS:
        return "counting"
    if a in ("before", "after") or any(
        k in q for k in (" before ", " after ", "first time", "last time",
                         " while ", "between")
    ):
        return "sequencing"
    return "open"


# ── CSV reading (chunked) ─────────────────────────────────────────────────────

def _resolve_csv(csv_arg: str) -> Path:
    p = Path(csv_arg)
    if p.is_file():
        return p
    if p.is_dir():
        csvs = sorted(p.rglob("*.csv"))  # recurse: AGQA nests under balanced/ etc.
        if not csvs:
            sys.exit(f"ERROR: no .csv files found under {p}")
        # Prefer the balanced *Test* split for evaluation: test > balanced.
        def _score(c: Path) -> int:
            s = str(c).lower()
            return ("test" in c.name.lower()) * 4 + ("balanced" in s) * 2
        best = max(csvs, key=_score)
        if len(csvs) > 1:
            print(f"[csv] {len(csvs)} CSVs found under {p}; using '{best}'")
        return best
    sys.exit(f"ERROR: --csv path not found: {p}")


def _sample_rows(
    csv_path: Path,
    num_videos: int,
    per_video: int,
    max_questions: int,
    seed: int,
    restrict_videos: set[str] | None,
) -> tuple[list[dict], dict[str, str | None]]:
    """Stream the CSV in chunks and collect a balanced sample.

    Returns (rows, column_mapping). Each row is a dict with normalized keys:
    question, answer, video_id, category, id.
    """
    import pandas as pd

    rng = random.Random(seed)
    by_video: dict[str, list[dict]] = defaultdict(list)
    mapping: dict[str, str | None] | None = None

    reader = pd.read_csv(csv_path, chunksize=50_000, dtype=str, keep_default_na=False)
    for chunk in reader:
        if mapping is None:
            mapping = _detect_columns(list(chunk.columns))
            print(f"[csv] columns: {list(chunk.columns)}")
            print(f"[csv] detected mapping: {mapping}")
            for required in ("question", "answer", "video_id"):
                if mapping[required] is None:
                    sys.exit(
                        f"ERROR: could not detect a '{required}' column. "
                        f"Edit _COL_CANDIDATES['{required}'] in this script to match "
                        f"one of: {list(chunk.columns)}"
                    )

        q_col, a_col, v_col = mapping["question"], mapping["answer"], mapping["video_id"]
        c_col, id_col = mapping["category"], mapping["id"]

        for _, r in chunk.iterrows():
            vid = str(r[v_col]).strip()
            if not vid:
                continue
            if restrict_videos is not None and vid not in restrict_videos:
                continue
            if restrict_videos is None and len(by_video) >= num_videos and vid not in by_video:
                continue  # already have enough distinct videos
            question = str(r[q_col]).strip()
            answer = str(r[a_col]).strip()
            by_video[vid].append({
                "question": question,
                "answer":   answer,
                "video_id": vid,
                "category": _norm_category(r[c_col]) if c_col
                            else _infer_category(question, answer),
                "id":       str(r[id_col]).strip() if id_col else "",
            })

        # Early stop: enough videos each with enough candidate questions.
        if restrict_videos is None:
            ready = [v for v, rows in by_video.items() if len(rows) >= per_video]
            if len(ready) >= num_videos:
                break

    if mapping is None:
        sys.exit("ERROR: CSV produced no rows.")

    # Choose videos
    videos = sorted(by_video.keys())
    if restrict_videos is None and len(videos) > num_videos:
        videos = sorted(rng.sample(videos, num_videos))

    # Per-video balanced-by-category sampling
    sampled: list[dict] = []
    for vid in videos:
        rows = by_video[vid]
        by_cat: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            by_cat[row["category"]].append(row)
        for cat in by_cat:
            rng.shuffle(by_cat[cat])
        # round-robin across categories until per_video reached
        picked: list[dict] = []
        cats = sorted(by_cat.keys())
        ci = 0
        while len(picked) < per_video and any(by_cat[c] for c in cats):
            c = cats[ci % len(cats)]
            if by_cat[c]:
                picked.append(by_cat[c].pop())
            ci += 1
        sampled.extend(picked)

    rng.shuffle(sampled)
    if len(sampled) > max_questions:
        sampled = sampled[:max_questions]
    return sampled, mapping


# ── Translation (cached) ──────────────────────────────────────────────────────

# Bump this whenever the prompts below change — it invalidates the on-disk cache
# so stale translations made with an older prompt are not silently reused.
_PROMPT_VERSION = 3

_Q_PROMPT = """\
你是专业的中英翻译。下面是一道关于「一个人做日常家务活动的短视频」的英文问题，请翻译成自然、准确的简体中文。

要求：
1. 完整保留原句的每一个子句和限定条件，尤其是表示时间先后 / 同时的结构，一个都不能漏：
   before→之前、after→之后、while→……的同时、first→第一次 / 最先、last→最后一次 / 最后、between→之间。
2. 按日常生活、动作的语义选词，不要用物理 / 抽象义。例如：vacuum=吸尘器（不是「真空」）、
   interact with=接触 / 互动（不是「相互作用」）、hold=拿着 / 握着、tidy=整理、lean on=倚靠。
3. 保持疑问句形式；只输出译文，不要引号、解释或任何多余文字。

英文：{text}"""

_A_PROMPT = """\
下面是针对某个问题的英文答案，请翻译成简体中文。务必结合问题选择正确词义
（例如问题在问「吸尘器还是袋子」时，bag=袋子，而不是「集尘袋」；before=之前、after=之后）。
只输出答案译文，不要引号或解释。

问题：{context}
英文答案：{text}"""


class _Translator:
    def __init__(self, cache_path: Path, dry_run: bool):
        self.cache_path = cache_path
        self.dry_run = dry_run
        self.cache: dict[str, str] = {}
        if cache_path.exists():
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("version") == _PROMPT_VERSION:
                self.cache = raw.get("entries", {})
            else:
                print(f"[translate] cache prompt-version changed → discarding "
                      f"{len(raw.get('entries', raw)) if isinstance(raw, dict) else 0} stale entries")
        self._client = None
        self._model = None

    def _ensure_client(self):
        if self._client is not None:
            return
        from openai import OpenAI
        from src.config import get_settings
        cfg = get_settings()
        self._client = OpenAI(
            base_url=cfg.active_llm.base_url,
            api_key=cfg.dashscope_api_key or "token-abc",
        )
        self._model = cfg.active_llm.model_name

    def translate(self, text: str, kind: str = "question", context: str = "") -> str:
        """kind: 'question' or 'answer'. context: the question, used to
        disambiguate word sense when translating a bare answer."""
        text = (text or "").strip()
        if not text:
            return ""
        # deterministic shortcut for binary answers
        if text.lower() in _YES_NO_ZH:
            return _YES_NO_ZH[text.lower()]
        if self.dry_run:
            return text  # pass-through, no API cost
        key = f"{kind}:{context}|{text}"
        if key in self.cache:
            return self.cache[key]
        self._ensure_client()
        template = _A_PROMPT if kind == "answer" else _Q_PROMPT
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user",
                           "content": template.format(text=text, context=context)}],
                max_tokens=256,
                temperature=0.0,
            )
            zh = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[translate][WARN] failed for {text[:40]!r}: {e}")
            zh = text
        self.cache[key] = zh
        return zh

    def flush(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps({"version": _PROMPT_VERSION, "entries": self.cache},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Build Chinese benchmark from AGQA CSV")
    ap.add_argument("--csv", default="data/agqa/csvs",
                    help="AGQA CSV file, or a dir containing CSVs")
    ap.add_argument("--video-dir", default="data/videos/charades",
                    help="where Charades <video_id>.mp4 live; if it already "
                         "contains mp4s, sampling is restricted to those")
    ap.add_argument("--num-videos", type=int, default=10)
    ap.add_argument("--per-video", type=int, default=7)
    ap.add_argument("--max-questions", type=int, default=70)
    ap.add_argument("--out", default="benchmarks/agqa_zh_small.json")
    ap.add_argument("--cache", default="benchmarks/agqa_translation_cache.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true",
                    help="skip translation (pass-through English), no API cost")
    args = ap.parse_args()

    csv_path = _resolve_csv(args.csv)
    print(f"[csv] reading {csv_path}")

    # If the user already downloaded some videos, only sample among those.
    video_dir = Path(args.video_dir)
    restrict: set[str] | None = None
    if video_dir.is_dir():
        present = {p.stem for p in video_dir.glob("*.mp4")}
        if present:
            restrict = present
            print(f"[videos] restricting to {len(present)} videos present in {video_dir}")
    if restrict is None:
        print(f"[videos] no local videos found; will sample {args.num_videos} "
              f"video_ids from the CSV (download exactly those afterwards)")

    rows, _mapping = _sample_rows(
        csv_path, args.num_videos, args.per_video, args.max_questions,
        args.seed, restrict,
    )
    vids = sorted({r["video_id"] for r in rows})
    print(f"\n[sample] {len(rows)} questions across {len(vids)} videos")
    print(f"[sample] video_ids: {vids}")
    cat_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        cat_counts[r["category"]] += 1
    print(f"[sample] category distribution: {dict(cat_counts)}")
    if restrict is None:
        print("\n>>> Download these Charades videos to "
              f"{video_dir}/<video_id>.mp4 before running the benchmark:")
        for v in vids:
            print(f"      {v}.mp4")

    # Translate + build records
    tr = _Translator(Path(args.cache), args.dry_run)
    out_records = []
    for i, r in enumerate(rows):
        q_zh = tr.translate(r["question"], kind="question")
        a_zh = tr.translate(r["answer"], kind="answer", context=r["question"])
        out_records.append({
            "id": r["id"] or f"agqa_{i:03d}",
            "video": f"{args.video_dir}/{r['video_id']}.mp4",
            "question": q_zh,
            "reference_answer": a_zh,
            "category": r["category"],
            "key_facts": [a_zh] if a_zh else [],
            "_source": {"video_id": r["video_id"], "en_question": r["question"],
                        "en_answer": r["answer"]},
        })
        if not args.dry_run and (i + 1) % 10 == 0:
            tr.flush()
            print(f"[translate] {i + 1}/{len(rows)} done")
    if not args.dry_run:
        tr.flush()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(out_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    mode = "DRY-RUN (English pass-through)" if args.dry_run else "translated"
    print(f"\n[done] wrote {len(out_records)} questions ({mode}) → {out_path}")


if __name__ == "__main__":
    main()
