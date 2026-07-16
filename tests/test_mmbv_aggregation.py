"""Official MMBench-Video aggregation (VLMEvalKit get_dimension_rating replica).

Guards the multi-label semantics: a question counts toward EVERY leaf in its
`dimensions` list and every coarse bucket it intersects; 'all' scores judge
failures (-1) as 0 while 'valid' excludes them; Overall(all) must equal the
flat per-question mean the runner has always reported (regression anchor).
"""
from __future__ import annotations

import pytest

from src.eval.run_benchmark import (
    _aggregate,
    _aggregate_mmbv_official,
    _mean,
    _mmbv_official_buckets,
    _score_of,
)


def _row(qid: str, dims: list[str], score: float, category: str) -> dict:
    return {
        "id": qid,
        "video": "v.mp4",
        "category": category,
        "dimensions": dims,
        "scores": {"mmbv": score},
        "tool_calls": 0,
        "time_sec": 1.0,
        "tokens": 100,
    }


# Multi-label rows spanning Perception and Reasoning, incl. a judge failure (-1)
# and a cross-L2 multi-label question (TR + FP-S).
TRIAL = [
    _row("q1", ["Hallucination"], 3.0, "HL"),
    _row("q2", ["Causal Reasoning", "Object Recognition"], 2.0, "TR"),
    _row("q3", ["Counting"], -1.0, "FP-S"),
    _row("q4", ["Mathematical Calculation"], 0.0, "LR"),
]


def test_buckets_match_official_construction():
    coarse, fine = _mmbv_official_buckets()
    assert len(fine) == 26
    assert set(coarse) == {"CP", "FP-S", "FP-C", "HL", "LR", "AR", "RR", "CSR",
                           "TR", "Perception", "Reasoning", "Overall"}
    assert set(coarse["Perception"]) == set(
        coarse["CP"] + coarse["FP-C"] + coarse["FP-S"] + coarse["HL"])
    assert set(coarse["Overall"]) == set(fine)


def test_fine_multi_label_and_failure_handling():
    agg = _aggregate_mmbv_official([TRIAL])
    fine = agg["fine"]
    # q2 counts toward BOTH of its leaves
    assert fine["Causal Reasoning"]["all_mean"] == 2.0
    assert fine["Object Recognition"]["all_mean"] == 2.0
    # judge failure: 'all' scores it 0, 'valid' has nothing left
    assert fine["Counting"] == {
        "n": 1, "n_valid": 0, "all_mean": 0.0, "all_std": 0.0,
        "valid_mean": None, "valid_std": None,
    }
    # untouched leaf reports empty, not zero
    assert fine["Video Topic"]["n"] == 0
    assert fine["Video Topic"]["all_mean"] is None


def test_coarse_multi_label_all_vs_valid():
    coarse = _aggregate_mmbv_official([TRIAL])["coarse"]
    # FP-S collects q2 (Object Recognition) and q3 (Counting, failed): [2, -1]
    assert coarse["FP-S"]["n"] == 2
    assert coarse["FP-S"]["all_mean"] == pytest.approx(1.0)    # (2+0)/2
    assert coarse["FP-S"]["valid_mean"] == pytest.approx(2.0)  # failure excluded
    assert coarse["FP-S"]["n_valid"] == 1
    # rollups: Perception = q1,q2,q3; Reasoning = q2,q4; Overall = all four
    assert coarse["Perception"]["all_mean"] == pytest.approx((3 + 2 + 0) / 3, abs=1e-3)
    assert coarse["Perception"]["valid_mean"] == pytest.approx(2.5)
    assert coarse["Reasoning"]["all_mean"] == pytest.approx(1.0)
    assert coarse["Overall"]["n"] == 4
    assert coarse["Overall"]["all_mean"] == pytest.approx(1.25)          # (3+2+0+0)/4
    assert coarse["Overall"]["valid_mean"] == pytest.approx(5 / 3, abs=1e-3)


def test_overall_all_equals_legacy_flat_mean():
    # Regression anchor: Overall(all) is mathematically the flat per-question
    # mean with -1 -> 0, i.e. exactly what the runner's overall_mean reports.
    coarse = _aggregate_mmbv_official([TRIAL])["coarse"]
    flat = _mean([_score_of(r, "mmbv") for r in TRIAL])
    assert coarse["Overall"]["all_mean"] == pytest.approx(flat)


def test_mean_std_over_trials():
    trial2 = [dict(r, scores={"mmbv": r["scores"]["mmbv"]}) for r in TRIAL]
    trial2[0] = _row("q1", ["Hallucination"], 1.0, "HL")  # 3 -> 1 in trial 2
    coarse = _aggregate_mmbv_official([TRIAL, trial2])["coarse"]
    # Overall(all): trial1 = 1.25, trial2 = (1+2+0+0)/4 = 0.75
    assert coarse["Overall"]["all_mean"] == pytest.approx(1.0)
    assert coarse["Overall"]["all_std"] == pytest.approx(0.25)


def test_paper_table_renders_table3_layout():
    from src.eval.run_benchmark import _mmbv_paper_lines

    off = _aggregate_mmbv_official([TRIAL])
    text = "\n".join(_mmbv_paper_lines({"agent_v2": off}))
    assert "| Model | Overall Mean | CP | FP-S | FP-C | HL | *P. Mean* " \
           "| LR | AR | RR | CSR | TR | *R. Mean* |" in text
    # Overall(all) of TRIAL is 1.25; untouched dims render as em-dash
    assert "| agent_v2 | **1.25** |" in text
    assert "| — |" in text
    assert "NOT directly comparable" in text


def test_aggregate_wires_official_only_for_mmbv_with_dimensions():
    agg = _aggregate([TRIAL], scorers=("mmbv",))
    assert "mmbv_official" in agg
    assert agg["scorers"]["mmbv"]["overall_mean"] == pytest.approx(
        agg["mmbv_official"]["coarse"]["Overall"]["all_mean"])
    # rows without dimensions (e.g. AGQA) must not produce the official block
    bare = [dict(r, dimensions=[]) for r in TRIAL]
    assert "mmbv_official" not in _aggregate([bare], scorers=("mmbv",))
