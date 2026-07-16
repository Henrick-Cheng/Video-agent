"""Re-aggregate cached mmbv results under the official MMBench-Video protocol.

Zero API cost: reads the per-question answers + judge scores already dumped by
run_benchmark (the `raw` section), joins each question's multi-label leaf
`dimensions` from the benchmark JSON, and re-runs the aggregation/report with
the official VLMEvalKit `get_dimension_rating` semantics (multi-label coarse +
fine buckets, all/valid variants). Use it to correct reports produced by the
old single-label aggregation without re-running inference or the judge.

Also accepts the raw-copy output of scripts/rejudge_gpt4.py, so a gpt-4-turbo
re-judge gets the same official breakdown.

Usage:
    python -m scripts.reaggregate_mmbv docs/benchmark_mmbv_final.json \
        --benchmark benchmarks/mmbv_150.json \
        --output docs/benchmark_mmbv_final_official_agg.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.eval.run_benchmark import _aggregate, _build_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Official (multi-label) re-aggregation of cached mmbv results")
    parser.add_argument("results", nargs="?", default="docs/benchmark_mmbv_final.json",
                        help="raw results JSON produced by run_benchmark (or rejudge_gpt4)")
    parser.add_argument("--benchmark", default="benchmarks/mmbv_150.json",
                        help="benchmark JSON supplying per-question dimensions")
    parser.add_argument("--output", default=None,
                        help="markdown output (default: <results>_official_agg.md)")
    args = parser.parse_args()

    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    raw: dict[str, list[list[dict]]] = data["raw"]
    meta = data.get("meta", {})
    scorers = tuple(meta.get("scorers") or ["mmbv"])
    if "mmbv" not in scorers:
        scorers = scorers + ("mmbv",)

    dims = {q["id"]: (q.get("_source") or {}).get("dimensions", [])
            for q in json.loads(Path(args.benchmark).read_text(encoding="utf-8"))}
    missing: set[str] = set()
    for trials in raw.values():
        for trial in trials:
            for r in trial:
                if not r.get("dimensions"):
                    r["dimensions"] = dims.get(r["id"], [])
                    if not r["dimensions"]:
                        missing.add(r["id"])
    if missing:
        print(f"[WARN] {len(missing)} question(s) have no dimensions in "
              f"{args.benchmark}: {sorted(missing)[:5]}...")

    n_runs = max(len(trials) for trials in raw.values())
    results_by_method = {m: _aggregate(trials, scorers) for m, trials in raw.items()}
    for method, agg in results_by_method.items():
        if "mmbv_official" not in agg:
            print(f"[WARN] {method}: no mmbv_official aggregation produced "
                  "(rows lack dimensions?)")

    report = _build_report(results_by_method, n_runs,
                           meta.get("video", "?"), args.benchmark,
                           raw_by_method=raw, scorers=scorers)
    out_md = Path(args.output or Path(args.results).with_suffix("").name + "_official_agg.md")
    if args.output is None:
        out_md = Path(args.results).parent / out_md.name
    out_md.write_text(report, encoding="utf-8")

    out_json = out_md.with_suffix(".json")
    out_json.write_text(
        json.dumps({"meta": {**meta, "scorers": list(scorers),
                             "reaggregated_from": str(args.results)},
                    "results": results_by_method,
                    "raw": raw}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"report → {out_md}\njson   → {out_json}")

    for method, agg in results_by_method.items():
        off = agg.get("mmbv_official")
        if off:
            ov = off["coarse"]["Overall"]
            print(f"{method:16s} Overall(all)={ov['all_mean']}"
                  f"  Overall(valid)={ov['valid_mean']}  n={ov['n']}")


if __name__ == "__main__":
    main()
