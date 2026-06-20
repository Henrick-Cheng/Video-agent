"""Re-judge cached mmbv answers with a paper-grade judge (e.g. gpt-4-turbo).

Zero inference cost: reads the answers already produced by run_benchmark
(docs/benchmark_mmbv_final.json) and only re-runs the MMBench-Video judge with
a different JUDGE_* endpoint. Reports the gpt-4 mean per method and its
agreement with the original qwen-max scores (judge-noise band).

Usage (when an OpenAI key is available):
    JUDGE_BASE_URL=https://api.openai.com/v1 \
    JUDGE_MODEL=gpt-4-turbo \
    JUDGE_API_KEY=sk-... \
    python -m scripts.rejudge_gpt4 docs/benchmark_mmbv_final.json
"""
import json
import sys
from statistics import mean

from src.eval.run_benchmark import _judge_mmbv, _judge_model


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/benchmark_mmbv_final.json"
    bench = sys.argv[2] if len(sys.argv) > 2 else "benchmarks/mmbv_150.json"
    data = json.load(open(path))
    raw = data["raw"]
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

    json.dump(out, open(path.replace(".json", f".rejudge_{judge}.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"\nsaved → {path.replace('.json', f'.rejudge_{judge}.json')}")


if __name__ == "__main__":
    main()
