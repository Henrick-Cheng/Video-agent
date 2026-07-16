"""Re-judge cached mmbv answers with a paper-grade judge (e.g. gpt-4-turbo).

Zero inference cost: reads the answers already produced by run_benchmark
(docs/results/benchmark_mmbv_final.json) and only re-runs the MMBench-Video judge with
a different JUDGE_* endpoint. Reports the new judge's mean per method and its
agreement with the original scores (judge-noise band), and dumps a raw-structure
copy with the re-judged scores so scripts/reaggregate_mmbv.py can produce the
full official (multi-label) dimension breakdown from it:

    python -m scripts.reaggregate_mmbv docs/results/benchmark_mmbv_final.rejudge_gpt-4-turbo.json

Usage (OPENAI_API_KEY stored in .env; a gpt-* JUDGE_MODEL auto-selects the
OpenAI endpoint + that key, so one variable switches the judge):
    JUDGE_MODEL=gpt-4-turbo python -m scripts.rejudge_gpt4 docs/results/benchmark_mmbv_final.json

Explicit JUDGE_BASE_URL / JUDGE_API_KEY still override (e.g. a GPT proxy).
"""
import copy
import json
import sys
from statistics import mean

from src.eval.run_benchmark import _judge_mmbv, _judge_model


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/results/benchmark_mmbv_final.json"
    bench = sys.argv[2] if len(sys.argv) > 2 else "benchmarks/mmbv_150.json"
    data = json.load(open(path))
    raw = copy.deepcopy(data["raw"])
    # raw dump stores no reference_answer — join gold from the benchmark by id.
    gold = {q["id"]: q["reference_answer"] for q in json.load(open(bench))}
    judge = _judge_model()
    print(f"Re-judging {path} with JUDGE_MODEL={judge}\n")

    out = {}
    for method, trials in raw.items():
        new_all, agree, n = [], 0, 0
        for trial in trials:
            for r in trial:
                gpt = _judge_mmbv(r["question"], gold.get(r["id"], ""),
                                  r["answer"])
                old = r["scores"].get("mmbv", -1)
                r["scores"]["mmbv"] = gpt  # raw -1 convention preserved
                new_all.append(max(gpt, 0))
                # exact-integer agreement with the original judge
                if gpt == old:
                    agree += 1
                n += 1
        out[method] = {
            "n": n,
            f"{judge}_mean": round(mean(new_all), 3) if new_all else 0.0,
            "exact_agreement_with_orig": round(agree / n, 3) if n else 0.0,
        }
        print(f"{method:16s} {judge} mean={out[method][f'{judge}_mean']:.3f}  "
              f"agreement={out[method]['exact_agreement_with_orig']:.3f}")

    summary_path = path.replace(".json", f".rejudge_{judge}.summary.json")
    json.dump(out, open(summary_path, "w"), ensure_ascii=False, indent=2)

    # Raw-structure copy with the re-judged scores — reaggregate_mmbv input.
    raw_path = path.replace(".json", f".rejudge_{judge}.json")
    meta = {**data.get("meta", {}), "judge_model": judge, "rejudged_from": path}
    json.dump({"meta": meta, "raw": raw}, open(raw_path, "w"),
              ensure_ascii=False, indent=2)
    print(f"\nsummary → {summary_path}\nraw     → {raw_path}")


if __name__ == "__main__":
    main()
