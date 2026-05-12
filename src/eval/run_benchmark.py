"""
run_benchmark.py — Chinese Video QA benchmark runner.

Three methods compared:
  agent       : Full ReAct Agent (scene graph + tools)
  rag_only    : Build full scene graph once, LLM answers from graph text
  vlm_direct  : Send raw sampled frames + question directly to VLM

LLM-as-Judge: qwen-plus scores each answer 0 / 0.5 / 1 against key_facts.
Each method runs n_runs times; mean ± std reported.

Usage:
    python -m src.eval.run_benchmark \\
        --video data/videos/test1.mp4 \\
        --benchmark benchmarks/cn_video_qa_v1.json \\
        --runs 3 \\
        --methods agent,rag_only,vlm_direct \\
        --output docs/benchmark_results.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Judge prompt ──────────────────────────────────────────────────────────────

_JUDGE_PROMPT = """\
你是严格的视频问答评测专家。请判断候选答案的质量。

【评分标准】
- 1.0：候选答案包含所有关键事实，语义正确
- 0.5：候选答案包含超过一半的关键事实，基本方向正确但有遗漏
- 0.0：候选答案错误、无关、或关键事实命中率低于50%

【注意】
- 数字必须精确（"2个" vs "3个" 得0分）
- 语义等价词可接受（"大厅" ≈ "准备区"）
- 只输出一个数字：0、0.5 或 1，不要解释

问题: {question}
参考答案: {reference}
关键事实（必须命中）: {key_facts}
候选答案: {candidate}

分数（只输出 0、0.5 或 1）："""


# ── Token tracker ─────────────────────────────────────────────────────────────

class _TrialStats:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.api_calls = 0

    def add(self, usage):
        if usage is None:
            return
        self.prompt_tokens += getattr(usage, "prompt_tokens", 0)
        self.completion_tokens += getattr(usage, "completion_tokens", 0)
        self.api_calls += 1

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def est_cost_rmb(self):
        # qwen-plus ~0.008 yuan/1K tokens; qwen-vl-plus ~0.008 yuan/1K text tokens
        return self.total_tokens / 1000 * 0.008


# ── Method implementations ────────────────────────────────────────────────────

def _build_session(video_path: str):
    from src.memory.session import VideoSession
    return VideoSession(video_path=video_path)


def _prebuild_graph(session, frame_count: int = 8) -> _TrialStats:
    """Extract frames and build full scene graph. Returns token stats."""
    from src.tools.keyframe import make_extract_keyframes
    from src.tools.scene_graph_builder import make_build_scene_graph
    from src.config import get_settings

    cfg = get_settings()
    stats = _TrialStats()

    kf_tool = make_extract_keyframes(session)
    sg_tool = make_build_scene_graph(session)

    result = json.loads(kf_tool.invoke({"strategy": "uniform", "count": frame_count}))
    frame_ids = ",".join(result["frame_ids"])
    sg_tool.invoke({"frame_ids": frame_ids, "focus_entities": ""})
    return stats


def _answer_agent(session, question: str) -> tuple[str, int, _TrialStats]:
    """Answer using full ReAct agent. Returns (answer, tool_calls, stats)."""
    from src.agents.react_agent import build_agent
    from src.config import get_settings

    cfg = get_settings()
    agent = build_agent(session)
    rl = getattr(agent, "_va_max_iterations", 6) * 3 + 1

    result = agent.invoke(
        {"messages": [("user", question)]},
        config={"recursion_limit": rl},
    )
    msgs = result.get("messages", [])
    answer = msgs[-1].content if msgs else ""
    tool_calls = sum(1 for m in msgs if getattr(m, "type", "") == "tool")

    # Estimate tokens from message lengths (API usage not easily available in LangGraph)
    stats = _TrialStats()
    total_chars = sum(len(str(getattr(m, "content", ""))) for m in msgs)
    stats.prompt_tokens = int(total_chars / 3)
    stats.completion_tokens = int(len(answer) / 3)
    stats.api_calls = tool_calls + 1

    return answer, tool_calls, stats


def _answer_rag_only(session, question: str) -> tuple[str, int, _TrialStats]:
    """LLM answers from scene graph text only."""
    from openai import OpenAI
    from src.config import get_settings
    from src.perception.vl_client import get_llm_client

    cfg = get_settings()
    graph_text = session.scene_graph.to_text()

    llm = get_llm_client()
    stats = _TrialStats()

    prompt = (
        f"你是视频内容分析助手。根据以下场景图信息回答问题，不要超出场景图内容。\n\n"
        f"{graph_text}\n\n"
        f"问题：{question}\n\n"
        f"请给出简洁准确的回答（2–4句）："
    )

    try:
        resp = OpenAI(
            base_url=cfg.active_llm.base_url,
            api_key=cfg.dashscope_api_key or "token-abc",
        ).chat.completions.create(
            model=cfg.active_llm.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.1,
        )
        stats.add(resp.usage)
        answer = resp.choices[0].message.content or ""
    except Exception as e:
        answer = f"[ERROR] {e}"

    return answer, 0, stats


def _answer_vlm_direct(session, question: str) -> tuple[str, int, _TrialStats]:
    """Send sampled frames + question directly to VLM."""
    from src.perception.vl_client import get_vl_client
    from src.config import get_settings

    cfg = get_settings()
    stats = _TrialStats()

    # Use cached frames (already extracted during prebuild; take up to 4 evenly)
    frames = list(session.cached_frames.values())
    if not frames:
        return "[ERROR] no frames in session", 0, stats

    step = max(1, len(frames) // 4)
    selected = [f for f in frames[::step] if f.path and Path(f.path).exists()][:4]

    if not selected:
        return "[ERROR] no valid frame files", 0, stats

    vl = get_vl_client()
    prompt = f"请根据这些视频帧回答问题：{question}\n\n请给出简洁准确的回答（2–4句）。"

    try:
        answer = vl.call_multi([f.path for f in selected], prompt)
    except Exception as e:
        answer = f"[ERROR] {e}"

    # Estimate: 4 frames × ~1500 img tokens + text
    stats.prompt_tokens = 4 * 1500 + len(prompt) // 3
    stats.completion_tokens = len(answer) // 3
    stats.api_calls = 1

    return answer, 0, stats


# ── Judge ─────────────────────────────────────────────────────────────────────

def _judge(question: str, reference: str, key_facts: list[str],
           candidate: str) -> float:
    """LLM-as-Judge: returns 0, 0.5, or 1."""
    from openai import OpenAI
    from src.config import get_settings

    cfg = get_settings()
    prompt = _JUDGE_PROMPT.format(
        question=question,
        reference=reference,
        key_facts="、".join(key_facts),
        candidate=candidate,
    )

    try:
        resp = OpenAI(
            base_url=cfg.active_llm.base_url,
            api_key=cfg.dashscope_api_key or "token-abc",
        ).chat.completions.create(
            model=cfg.active_llm.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16,
            temperature=0.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if "1" in raw and "0" not in raw.replace("1", ""):
            return 1.0
        if "0.5" in raw:
            return 0.5
        return 0.0
    except Exception:
        return 0.0


# ── Trial runner ──────────────────────────────────────────────────────────────

def run_trial(
    method: str,
    video_path: str,
    questions: list[dict],
) -> list[dict]:
    """Run all questions for one method in one trial. Returns per-question results."""
    session = _build_session(video_path)

    print(f"  [prebuild] extracting frames & building graph...")
    _prebuild_graph(session, frame_count=8)
    n_entities = len(session.scene_graph.entities)
    n_triplets = len(session.scene_graph)
    print(f"  [prebuild] graph: {n_entities} entities, {n_triplets} triplets")

    results = []
    for i, qa in enumerate(questions):
        q = qa["question"]
        print(f"  Q{i+1:02d} [{qa['category']}] {q[:40]}...")
        t0 = time.time()

        if method == "agent":
            answer, tool_calls, stats = _answer_agent(session, q)
        elif method == "rag_only":
            answer, tool_calls, stats = _answer_rag_only(session, q)
        elif method == "vlm_direct":
            answer, tool_calls, stats = _answer_vlm_direct(session, q)
        else:
            raise ValueError(f"Unknown method: {method}")

        elapsed = time.time() - t0
        score = _judge(q, qa["reference_answer"], qa["key_facts"], answer)
        print(f"         score={score} time={elapsed:.1f}s tools={tool_calls}")

        results.append({
            "id": qa["id"],
            "category": qa["category"],
            "question": q,
            "answer": answer,
            "score": score,
            "tool_calls": tool_calls,
            "time_sec": round(elapsed, 2),
            "tokens": stats.total_tokens,
        })

    return results


# ── Statistics helpers ────────────────────────────────────────────────────────

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _aggregate(all_trials: list[list[dict]]) -> dict:
    """Aggregate multiple trial result lists into mean/std stats."""
    categories = ["object", "attribute", "relation", "temporal", "count"]
    n = len(all_trials)

    # Overall accuracy per trial
    overall_scores = [_mean([r["score"] for r in trial]) for trial in all_trials]
    cat_scores: dict[str, list[float]] = {c: [] for c in categories}
    for trial in all_trials:
        by_cat: dict[str, list[float]] = {c: [] for c in categories}
        for r in trial:
            by_cat[r["category"]].append(r["score"])
        for c in categories:
            cat_scores[c].append(_mean(by_cat[c]) if by_cat[c] else 0.0)

    # Tool calls (only meaningful for agent)
    tool_calls_per_trial = [
        _mean([r["tool_calls"] for r in trial]) for trial in all_trials
    ]
    time_per_trial = [
        _mean([r["time_sec"] for r in trial]) for trial in all_trials
    ]
    tokens_per_q = [
        _mean([r["tokens"] for r in trial]) for trial in all_trials
    ]

    return {
        "overall_mean":   round(_mean(overall_scores), 3),
        "overall_std":    round(_std(overall_scores), 3),
        "by_category": {
            c: {
                "mean": round(_mean(cat_scores[c]), 3),
                "std":  round(_std(cat_scores[c]), 3),
            }
            for c in categories
        },
        "avg_tool_calls": round(_mean(tool_calls_per_trial), 1),
        "avg_time_sec":   round(_mean(time_per_trial), 1),
        "avg_tokens_per_q": int(_mean(tokens_per_q)),
    }


# ── Report generation ─────────────────────────────────────────────────────────

_CAT_LABELS = {
    "object":    "物体识别",
    "attribute": "实体属性",
    "relation":  "关系推理",
    "temporal":  "时序推理",
    "count":     "计数/出现",
}


def _build_report(results_by_method: dict[str, dict], n_runs: int,
                  video_path: str, bench_path: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Benchmark Results",
        "",
        f"> Video: `{video_path}`  |  Benchmark: `{bench_path}`  "
        f"|  Runs: {n_runs}  |  Generated: {ts}",
        "",
        "## Overall Accuracy",
        "",
        "| Method | Accuracy (mean ± std) | Avg Tool Calls | Avg Time (s) | Est. Tokens/Q |",
        "|--------|----------------------|----------------|--------------|---------------|",
    ]
    for method, agg in results_by_method.items():
        acc = f"{agg['overall_mean']:.3f} ± {agg['overall_std']:.3f}"
        tc = str(agg["avg_tool_calls"]) if method == "agent" else "—"
        lines.append(
            f"| **{method}** | {acc} | {tc} | {agg['avg_time_sec']} | {agg['avg_tokens_per_q']} |"
        )

    lines += ["", "## Per-Category Accuracy", ""]
    header = "| Category | " + " | ".join(results_by_method.keys()) + " |"
    sep = "|----------|" + "---------|" * len(results_by_method)
    lines += [header, sep]

    categories = ["object", "attribute", "relation", "temporal", "count"]
    for cat in categories:
        label = _CAT_LABELS[cat]
        vals = []
        for agg in results_by_method.values():
            c = agg["by_category"][cat]
            vals.append(f"{c['mean']:.3f}±{c['std']:.3f}")
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    lines += [
        "",
        "## Notes",
        "",
        "- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools",
        "- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only",
        "- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM",
        "- Judge: `qwen-plus-latest` LLM-as-Judge, scores 0 / 0.5 / 1 against `key_facts`",
        f"- Each method ran {n_runs} independent trials; mean ± std reported",
        "",
        "_TODO: Replace placeholder results with real benchmark run once API key is available._",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Video QA benchmark runner")
    parser.add_argument("--video", default="data/videos/test1.mp4")
    parser.add_argument("--benchmark", default="benchmarks/cn_video_qa_v1.json")
    parser.add_argument("--methods", default="agent,rag_only,vlm_direct")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", default="docs/benchmark_results.md")
    parser.add_argument(
        "--categories",
        default="",
        help="Comma-separated categories to run (default: all)",
    )
    args = parser.parse_args()

    # ── sanity checks ─────────────────────────────────────────────────────────
    from src.config import get_settings
    cfg = get_settings()
    if not cfg.dashscope_api_key and cfg.backend == "dashscope":
        print("ERROR: DASHSCOPE_API_KEY not set. Please export it or add to .env")
        sys.exit(1)

    bench_path = Path(args.benchmark)
    if not bench_path.exists():
        print(f"ERROR: benchmark file not found: {bench_path}")
        sys.exit(1)

    questions: list[dict] = json.loads(bench_path.read_text(encoding="utf-8"))

    if args.categories:
        cats = set(args.categories.split(","))
        questions = [q for q in questions if q["category"] in cats]
        print(f"Filtered to categories {cats}: {len(questions)} questions")

    methods = [m.strip() for m in args.methods.split(",")]
    results_by_method: dict[str, dict] = {}

    print(f"\n{'='*60}")
    print(f"  Video QA Benchmark")
    print(f"  Video    : {args.video}")
    print(f"  Questions: {len(questions)}")
    print(f"  Methods  : {methods}")
    print(f"  Runs     : {args.runs}")
    print(f"{'='*60}\n")

    for method in methods:
        print(f"\n{'─'*60}")
        print(f"  METHOD: {method.upper()}")
        print(f"{'─'*60}")

        all_trials: list[list[dict]] = []
        for run_i in range(args.runs):
            print(f"\n  Run {run_i + 1}/{args.runs}")
            trial = run_trial(method, args.video, questions)
            all_trials.append(trial)
            acc = _mean([r["score"] for r in trial])
            print(f"  → Run accuracy: {acc:.3f}")

        agg = _aggregate(all_trials)
        results_by_method[method] = agg

        print(f"\n  {method} summary: {agg['overall_mean']:.3f} ± {agg['overall_std']:.3f}")

    # ── Print summary table ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"\n{'Method':<15} {'Accuracy':>15} {'Time(s)':>10} {'Tokens/Q':>10}")
    print("─" * 55)
    for method, agg in results_by_method.items():
        acc = f"{agg['overall_mean']:.3f}±{agg['overall_std']:.3f}"
        print(f"{method:<15} {acc:>15} {agg['avg_time_sec']:>10.1f} {agg['avg_tokens_per_q']:>10}")

    # Per-category breakdown
    print(f"\n{'Category':<16}", end="")
    for method in methods:
        print(f" {method:>15}", end="")
    print()
    print("─" * (16 + 16 * len(methods)))
    for cat in ["object", "attribute", "relation", "temporal", "count"]:
        label = _CAT_LABELS[cat]
        print(f"{label:<16}", end="")
        for method in methods:
            c = results_by_method[method]["by_category"][cat]
            print(f" {c['mean']:.3f}±{c['std']:.3f}  ", end="")
        print()

    # ── Write markdown report ─────────────────────────────────────────────────
    report = _build_report(results_by_method, args.runs, args.video, args.benchmark)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\n  Report written to: {out_path}")
    print(f"{'='*60}\n")

    # Also dump raw JSON for later analysis
    raw_out = out_path.with_suffix(".json")
    raw_out.write_text(
        json.dumps({"meta": {"video": args.video, "runs": args.runs},
                    "results": results_by_method}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
