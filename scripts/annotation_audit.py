"""Estimate the annotation-noise ceiling of the mmbv_150 subset (Phase 14.3).

Some MMBench-Video gold answers are not supported by the video evidence the
pipeline can access (e.g. mmbv-0434: gold "asks the saleswoman" vs a transcript
about a press/touch/smell method) — these CAP the achievable mean below 3.0 for
EVERY method. This samples questions and classifies each gold as supported /
partial / unsupported given (L0 summary + full transcript), via an LLM judge.

PROXY DISCLOSURE: this uses the sparse-frame summary + ASR transcript, NOT human
review of the full video. It bounds the *transcript+gist-derivable* ceiling; a
gold answer needing fine visual detail may be flagged unsupported here yet be
answerable from frames. Treat the unsupported fraction as a rough floor on
annotation noise, anchored by the known 0434 case.

Usage:
    python -m scripts.annotation_audit --n 30 --seed 11
"""
import argparse
import json
import random

from src.config import get_settings
from src.eval.run_benchmark import _judge_client, _judge_model, _prepare_l0
from src.memory.session import VideoSession
from src.perception.asr import transcript_text

_PROMPT = """\
You are auditing a video-QA benchmark's GROUND-TRUTH answers.
Given only the video's global summary and full narration transcript, decide \
whether the provided ground-truth answer is SUPPORTED by this evidence.

Respond with exactly one word:
- supported   : the ground-truth is clearly derivable from the summary/transcript
- partial     : partially hinted but not clearly derivable
- unsupported : the evidence does not support (or contradicts) the ground-truth

Question: {q}
Ground-truth answer: {g}

[Global summary]
{summary}

[Narration transcript]
{tr}

Your one-word verdict:"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--bench", default="benchmarks/mmbv_150.json")
    args = ap.parse_args()

    qs = json.load(open(args.bench))
    sample = random.Random(args.seed).sample(qs, min(args.n, len(qs)))

    cfg = get_settings()
    sessions: dict[str, VideoSession] = {}
    rows, tally = [], {"supported": 0, "partial": 0, "unsupported": 0, "?": 0}

    for q in sample:
        vid = q["video"]
        if vid not in sessions:
            s = VideoSession(vid)
            _prepare_l0(s)               # builds summary + (cached) transcript
            sessions[vid] = s
        s = sessions[vid]
        prompt = _PROMPT.format(
            q=q["question"], g=q["reference_answer"],
            summary=s.global_summary or "(none)",
            tr=transcript_text(s.transcript) or "(no speech)",
        )
        try:
            resp = _judge_client().chat.completions.create(
                model=_judge_model(),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4, temperature=0.0,
            )
            v = (resp.choices[0].message.content or "").strip().lower()
            verdict = next((k for k in tally if k in v), "?")
        except Exception:
            verdict = "?"
        tally[verdict] += 1
        rows.append({"id": q["id"], "category": q["category"],
                     "verdict": verdict, "gold": q["reference_answer"][:60]})
        print(f"  {q['id']} [{q['category']:5s}] {verdict:11s} | {q['reference_answer'][:50]}")

    n = len(sample)
    unsup = tally["unsupported"]; part = tally["partial"]
    print(f"\n=== Annotation audit (n={n}, seed={args.seed}, judge={_judge_model()}) ===")
    print(f"  supported   {tally['supported']:2d}  ({tally['supported']/n:.0%})")
    print(f"  partial     {part:2d}  ({part/n:.0%})")
    print(f"  unsupported {unsup:2d}  ({unsup/n:.0%})")
    # Rough ceiling: unsupported contributes ~0, partial ~halves its max → mean<3.
    ceiling = (tally["supported"] * 3 + part * 1.5 + unsup * 0) / n / 3
    print(f"  → rough transcript+gist ceiling (norm 0-1): ~{ceiling:.2f}  "
          f"(PROXY — see header disclosure)")

    json.dump({"tally": tally, "n": n, "seed": args.seed, "rows": rows,
               "ceiling_proxy": round(ceiling, 3)},
              open("docs/results/annotation_audit.json", "w"), ensure_ascii=False, indent=2)
    print("saved → docs/results/annotation_audit.json")


if __name__ == "__main__":
    main()
