# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 1  |  Generated: 2026-07-17 17:38

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|------|
| **vlm_direct** | 1.700 ± 0.000 | — | 0.0 | 15.9 | 13304 | — | 13304 |
| **vlm_transcript** | 1.860 ± 0.000 | — | 0.0 | 15.9 | 13844 | — | 13844 |

## MMBench-Video Official Rating (multi-label, 0-3)

> VLMEvalKit `get_dimension_rating` semantics: each question counts toward **every** dimension it is tagged with (a question can appear in several rows). Cell = `all / valid` mean: *all* scores judge failures as 0 (official leaderboard variant); *valid* excludes them (`(vN)` marks buckets with failures). ± std over trials is an extension over the official single-run protocol. n = questions per bucket.

### Paper-style summary (Table-3 layout of the MMBench-Video paper)

| Model | Overall Mean | CP | FP-S | FP-C | HL | *P. Mean* | LR | AR | RR | CSR | TR | *R. Mean* |
|-------|------|----|----|----|----|----|----|----|----|----|----|----|----|
| vlm_direct | **1.70** | 1.71 | 2.06 | 1.06 | 0.60 | 1.58 | 1.27 | 2.14 | 2.21 | 2.23 | 1.67 | 1.88 |
| vlm_transcript | **1.86** | 2.06 | 2.19 | 1.18 | 0.73 | 1.72 | 1.64 | 2.36 | 2.29 | 2.38 | 1.82 | 2.06 |

> ⚠️ 150-question stratified subset (TR/HL oversampled) — rows are NOT directly comparable to published full-set (1,998-question) numbers; use for internal method comparison, or re-run on the full set before placing in the same table as leaderboard entries.

### L2 dimensions + rollups

| Dimension | n | vlm_direct | vlm_transcript |
|-----------|---|---------|---------|
| CP | 17 | 1.71±0.00 / 1.71 | 2.06±0.00 / 2.06 |
| FP-S | 36 | 2.06±0.00 / 2.06 | 2.19±0.00 / 2.19 |
| FP-C | 17 | 1.06±0.00 / 1.06 | 1.18±0.00 / 1.18 |
| HL | 15 | 0.60±0.00 / 0.60 | 0.73±0.00 / 0.73 |
| LR | 11 | 1.27±0.00 / 1.27 | 1.64±0.00 / 1.64 |
| AR | 14 | 2.14±0.00 / 2.14 | 2.36±0.00 / 2.36 |
| RR | 14 | 2.21±0.00 / 2.21 | 2.29±0.00 / 2.29 |
| CSR | 13 | 2.23±0.00 / 2.23 | 2.38±0.00 / 2.38 |
| TR | 33 | 1.67±0.00 / 1.67 | 1.82±0.00 / 1.82 |
| **Perception** | 78 | 1.58±0.00 / 1.58 | 1.72±0.00 / 1.72 |
| **Reasoning** | 83 | 1.88±0.00 / 1.88 | 2.06±0.00 / 2.06 |
| **Overall** | 150 | 1.70±0.00 / 1.70 | 1.86±0.00 / 1.86 |

### 26 leaf capabilities

| Dimension | n | vlm_direct | vlm_transcript |
|-----------|---|---------|---------|
| Video Topic | 7 | 2.00±0.00 / 2.00 | 2.14±0.00 / 2.14 |
| Video Emotion | 4 | 1.75±0.00 / 1.75 | 2.25±0.00 / 2.25 |
| Video Scene | 6 | 1.33±0.00 / 1.33 | 1.83±0.00 / 1.83 |
| Video Style | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| OCR | 16 | 1.94±0.00 / 1.94 | 2.25±0.00 / 2.25 |
| Object Recognition | 6 | 2.33±0.00 / 2.33 | 2.00±0.00 / 2.00 |
| Attribute Recognition | 2 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Event Recognition | 8 | 1.75±0.00 / 1.75 | 2.00±0.00 / 2.00 |
| Human Motion | 3 | 2.00±0.00 / 2.00 | 2.00±0.00 / 2.00 |
| Counting | 3 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Human-object Interaction | 6 | 1.00±0.00 / 1.00 | 1.00±0.00 / 1.00 |
| Human Interaction | 12 | 1.08±0.00 / 1.08 | 1.25±0.00 / 1.25 |
| Hallucination | 15 | 0.60±0.00 / 0.60 | 0.73±0.00 / 0.73 |
| Structuralized Image-Text Understanding | 5 | 1.60±0.00 / 1.60 | 1.80±0.00 / 1.80 |
| Mathematical Calculation | 6 | 1.00±0.00 / 1.00 | 1.50±0.00 / 1.50 |
| Physical Property | 5 | 2.40±0.00 / 2.40 | 2.40±0.00 / 2.40 |
| Function Reasoning | 6 | 2.00±0.00 / 2.00 | 2.17±0.00 / 2.17 |
| Identity Reasoning | 3 | 2.00±0.00 / 2.00 | 2.67±0.00 / 2.67 |
| Natural Relation | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Physical Relation | 8 | 2.00±0.00 / 2.00 | 2.00±0.00 / 2.00 |
| Social Relation | 5 | 2.40±0.00 / 2.40 | 2.60±0.00 / 2.60 |
| Common Sense Reasoning | 13 | 2.23±0.00 / 2.23 | 2.38±0.00 / 2.38 |
| Counterfactual Reasoning | 8 | 1.62±0.00 / 1.62 | 1.62±0.00 / 1.62 |
| Causal Reasoning | 22 | 1.82±0.00 / 1.82 | 2.04±0.00 / 2.04 |
| Future Prediction | 4 | 1.00±0.00 / 1.00 | 1.25±0.00 / 1.25 |

## Per-Video Accuracy — MMBench-Video official (0-3)

| Video | vlm_direct | vlm_transcript |
|-------|------|------|
| 4jOk3ajqJ2s_processed.mp4 | 3.000 | 3.000 |
| Qnyb73rf7gM_processed.mp4 | 1.000 | 1.000 |
| dSHcCllTCzY.mp4 | 3.000 | 3.000 |
| HtFrFZN8ud4.mp4 | 0.000 | 0.000 |
| Pfq9tqX_r-4.mp4 | 1.000 | 3.000 |
| bVceDFUlkX4.mp4 | 1.000 | 2.000 |
| a1ZNeTpMve8.mp4 | 0.000 | 0.000 |
| cHazQV45SPs.mp4 | 3.000 | 3.000 |
| ebFwtm1hUWM.mp4 | 3.000 | 2.000 |
| DrQzaGncGmw.mp4 | 2.000 | 1.000 |
| -9mIKCYg2vU.mp4 | 3.000 | 3.000 |
| u0GSFSvWDG4.mp4 | 0.000 | 0.000 |
| Mylca_onT_I.mp4 | 0.000 | 1.000 |
| YGE5Q2wgfs8.mp4 | 0.000 | 1.000 |
| RWkKNcGmUI0.mp4 | 2.000 | 2.000 |
| 115amzVdV44_processed.mp4 | 3.000 | 3.000 |
| umlonbnm1Kk.mp4 | 1.000 | 1.000 |
| zmHB11-V3cs.mp4 | 1.000 | 1.000 |
| zRRm1Kpx5zQ.mp4 | 3.000 | 3.000 |
| rdQrwBVRzEg.mp4 | 2.000 | 2.000 |
| iBIGBcGo1rY.mp4 | 3.000 | 3.000 |
| 3jQ_toeu314.mp4 | 1.333 | 1.667 |
| UIoqKfO8RJw.mp4 | 1.000 | 2.000 |
| z3yqHiQxlhg.mp4 | 1.500 | 2.000 |
| vBOWe1WK0Ig.mp4 | 2.000 | 2.000 |
| SX2Ajdf4-34.mp4 | 1.000 | 1.000 |
| d2ohLXJBykM.mp4 | 2.000 | 2.000 |
| mSaQXWoUHm0.mp4 | 1.000 | 3.000 |
| rQt4Q-ML7U4.mp4 | 2.000 | 2.000 |
| mfBNcc33EGA.mp4 | 2.500 | 2.500 |
| BbARfF2Gf64.mp4 | 1.500 | 2.000 |
| py6OsO_WSqU.mp4 | 0.000 | 0.000 |
| SEdkof4g8Y8.mp4 | 2.000 | 1.000 |
| Eer_CfDgqhY.mp4 | 2.000 | 2.000 |
| 2Ja6H_up6TQ.mp4 | 3.000 | 3.000 |
| opf_wezZTic.mp4 | 2.000 | 1.000 |
| tn3bGHxJH_M.mp4 | 0.000 | 0.000 |
| zm5bL2v876s.mp4 | 2.000 | 2.000 |
| RnDYM-EBsXM.mp4 | 3.000 | 3.000 |
| no9Ajy0tabs.mp4 | 3.000 | 3.000 |
| ccz1kfkdo2o.mp4 | 3.000 | 3.000 |
| qyOpdQO2__c.mp4 | 0.000 | 0.000 |
| h70GdtAkEOw.mp4 | 0.000 | 0.000 |
| b5soe5g0igs.mp4 | 0.000 | 0.000 |
| nJYKKyZFqzU.mp4 | 3.000 | 3.000 |
| 3cs8S_urAXU.mp4 | 1.000 | 1.000 |
| pod4x5NJoYI.mp4 | 3.000 | 3.000 |
| Mng2me2TNro.mp4 | 0.000 | 0.000 |
| jF31ICvl1T8.mp4 | 3.000 | 3.000 |
| QVzeW1_hyHI.mp4 | 2.000 | 1.000 |
| fYP4SryI9L0.mp4 | 2.000 | 2.000 |
| _Zt1EuIEhvw_processed.mp4 | 1.000 | 1.000 |
| 2mYHGn_Pd5M_processed.mp4 | 1.000 | 2.000 |
| Q1cDKWToTGA.mp4 | 0.500 | 0.500 |
| 1zLgiOaOzNI.mp4 | 2.000 | 1.000 |
| bS1ePEZZCDY_processed.mp4 | 1.000 | 1.000 |
| 8dgyPRA86K0.mp4 | 2.000 | 3.000 |
| c_lFunATvhk.mp4 | 3.000 | 3.000 |
| RTSrYhD-Qk0.mp4 | 3.000 | 3.000 |
| dxE80fpImj8.mp4 | 1.000 | 1.000 |
| V_Hn6pT4M-Y.mp4 | 3.000 | 3.000 |
| biAFfW-uiKI.mp4 | 0.000 | 0.000 |
| 0018ybk0K-E.mp4 | 3.000 | 3.000 |
| 2zTwYcdW0Ew.mp4 | 3.000 | 3.000 |
| LOxxhecSHQM.mp4 | 1.000 | 1.000 |
| XnABXVhqXI0.mp4 | 3.000 | 3.000 |
| GgqhnkkJTp8.mp4 | 1.500 | 2.000 |
| 9uBbgltCs94.mp4 | 2.000 | 2.000 |
| zON0wDD7VJY.mp4 | 1.000 | 1.000 |
| GhABIaANJCY.mp4 | 2.000 | 3.000 |
| Zvoxf_W1ZvA.mp4 | 3.000 | 3.000 |
| zBv_fuKyg5E.mp4 | 3.000 | 3.000 |
| O-17kqjsiFc_processed.mp4 | 3.000 | 3.000 |
| 9OxNk-d1PNw.mp4 | 0.000 | 1.000 |
| e_iZaS00xds.mp4 | 0.000 | 0.000 |
| ZVl-Lm_XaTI.mp4 | 3.000 | 3.000 |
| QH7GaLx5JYc.mp4 | 0.000 | 0.000 |
| xUkqUL5bXSE.mp4 | 0.000 | 1.000 |
| HxxfnxOIzdo.mp4 | 1.000 | 1.000 |
| rDWzQ6lZNpY.mp4 | 0.000 | 0.000 |
| QKHPOzA9Ge0_processed.mp4 | 3.000 | 3.000 |
| rhkkCDTkcvI_processed.mp4 | 0.000 | 3.000 |
| ApNRpFOKQrA.mp4 | 0.000 | 0.000 |
| W8OzZa16vtE.mp4 | 3.000 | 3.000 |
| r7COWvxlN5g_processed.mp4 | 3.000 | 3.000 |
| 0eKi5V1IOi0.mp4 | 3.000 | 3.000 |
| hHZvUeAdzeI.mp4 | 0.000 | 0.000 |
| qfUZBKDh9BY_processed.mp4 | 3.000 | 3.000 |
| YGSKW5AVBjc.mp4 | 3.000 | 3.000 |
| WCT6xM9jyzA.mp4 | 3.000 | 3.000 |
| PU7j9UF4lpA.mp4 | 1.000 | 1.000 |
| BY3nBVbUYjI.mp4 | 3.000 | 1.000 |
| 4Gb0lotHA8E.mp4 | 1.000 | 2.000 |
| S2nBBMbjS8w.mp4 | 3.000 | 3.000 |
| AkaEnPxMla8.mp4 | 3.000 | 3.000 |
| bRpUauseTVw.mp4 | 1.000 | 1.000 |
| q01PqUubacA.mp4 | 0.500 | 1.000 |
| EpFKDzmMnao_processed.mp4 | 2.000 | 3.000 |
| LEHR8YQNm_Q.mp4 | 0.000 | 0.000 |
| hq7nFVTFukc.mp4 | 1.000 | 3.000 |
| 68191uKawYw.mp4 | 3.000 | 3.000 |
| 5phZ6-eHbqM.mp4 | 3.000 | 2.000 |
| l1uE_pBqnvE.mp4 | 2.000 | 2.000 |
| tnMr9abBX7k.mp4 | 3.000 | 3.000 |
| ZNRSHr3b4uA.mp4 | 1.000 | 1.000 |
| 66XwG1CLHuU.mp4 | 3.000 | 3.000 |
| 9HsKNFr7xmI.mp4 | 3.000 | 3.000 |
| TseT4C38UAg.mp4 | 1.000 | 1.000 |
| uO8v6bjwRdo.mp4 | 0.000 | 0.000 |
| BfemWi1SKdw.mp4 | 0.000 | 0.000 |
| Zh3Yz3PiXZw_processed.mp4 | 1.000 | 2.000 |
| M7OiIun5NfQ.mp4 | 1.000 | 2.000 |
| X3COFNPpdDc_processed.mp4 | 0.000 | 1.000 |
| B363bRgVUUA_processed.mp4 | 1.000 | 1.000 |
| bTG65BRLaRE_processed.mp4 | 0.000 | 0.000 |
| lWCA_3GLrCE_processed.mp4 | 1.000 | 1.000 |
| T2XOiCM0OOA_processed.mp4 | 2.000 | 2.000 |
| cTA2rkKp6qo_processed.mp4 | 3.000 | 3.000 |
| ddzjFNvpZhM.mp4 | 3.000 | 3.000 |
| yVkdfJ9PkRQ.mp4 | 3.000 | 3.000 |
| 5eNhS0oaLHo_processed.mp4 | 3.000 | 3.000 |
| 9j_HWkrSxzI_processed.mp4 | 2.000 | 3.000 |
| QkPJzK9SnTg.mp4 | 2.000 | 2.000 |
| Mwc4ePLjkQ8_processed.mp4 | 1.000 | 1.000 |
| WydM_QmW1ec.mp4 | 3.000 | 3.000 |
| vNhORnwcQcU_processed.mp4 | 3.000 | 3.000 |
| IFQ9zQekRio_processed.mp4 | 1.000 | 1.000 |
| L8luXQhnAGk.mp4 | 0.000 | 0.000 |
| zXR93P8EnxM_processed.mp4 | 1.000 | 1.000 |
| khXSmQHenSk_processed.mp4 | 0.000 | 0.000 |
| kiwy_nV-hxE.mp4 | 2.000 | 3.000 |
| b9DW-tHrQB8.mp4 | 3.000 | 2.000 |
| G4DPefY6-NM.mp4 | 2.500 | 3.000 |
| 0luoGkddtYw_processed.mp4 | 2.000 | 3.000 |
| HRe90ySP38U_processed.mp4 | 3.000 | 3.000 |
| 9-r4VLHQRlM_processed.mp4 | 2.000 | 2.000 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **agent_v2**: Lazy-memory agent — per-video init is only a sparse-frame summary + local ASR transcript; the agent then decides at runtime which time windows to explore (explore_segment builds dense captions + indexed triplets on demand), with a confidence-driven loop (rate 1-3, ≤2 explores/round, ≤3 rounds)
- **agent_tiered**: Cost-aware agent — scene graph (or its summary, when >30 triplets) injected into context; the model decides at runtime whether to answer directly (one LLM call) or escalate to query/inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples N frames (default 4, see --vlm-frames), sends raw frames + question directly to VLM
- **vlm_transcript**: vlm_direct + the local ASR transcript prepended to the prompt — fairness baseline isolating the extra modality from the architecture
- **Frames/Q**: frames sent to the vision model per question (answer phase) — the guided-perception-budget metric
- **Prebuild frame budget**: duration-adaptive — one frame per ~15s, clamped to [8, 24] (Charades-length clips stay at the historical 8)
- **Token accounting**: all counts are real API-reported `usage` summed over every call the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully counted; VL calls include image tokens in prompt_tokens). No estimates. **Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the one-time scene-graph build over that video's questions (vlm_direct has no prebuild). Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted
- **MMBench-Video official (0-3)**: VLMEvalKit protocol replicated verbatim (semantic-similarity integer 0-3; multi-label `get_dimension_rating` aggregation with all/valid variants; judge failures → 0 in 'all', raw -1 kept in JSON). Judge model: `qwen-plus-latest` (official protocol uses gpt-4-turbo; swap via JUDGE_MODEL for paper numbers). Any run on fewer than the full 1,998 questions is a subset — NOT comparable to the official leaderboard
- Each method ran 1 independent trials; mean ± std reported over trials