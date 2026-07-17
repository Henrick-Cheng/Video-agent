# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 1  |  Generated: 2026-07-17 16:20

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|------|
| **vlm_direct** | 1.647 ± 0.000 | — | 38.1 | 31.4 | 26131 | — | 26131 |
| **vlm_transcript** | 1.787 ± 0.000 | — | 17.7 | 31.4 | 26660 | — | 26660 |

## MMBench-Video Official Rating (multi-label, 0-3)

> VLMEvalKit `get_dimension_rating` semantics: each question counts toward **every** dimension it is tagged with (a question can appear in several rows). Cell = `all / valid` mean: *all* scores judge failures as 0 (official leaderboard variant); *valid* excludes them (`(vN)` marks buckets with failures). ± std over trials is an extension over the official single-run protocol. n = questions per bucket.

### Paper-style summary (Table-3 layout of the MMBench-Video paper)

| Model | Overall Mean | CP | FP-S | FP-C | HL | *P. Mean* | LR | AR | RR | CSR | TR | *R. Mean* |
|-------|------|----|----|----|----|----|----|----|----|----|----|----|----|
| vlm_direct | **1.65** | 1.59 | 1.97 | 1.12 | 0.60 | 1.46 | 2.46 | 2.07 | 2.07 | 2.38 | 1.24 | 1.85 |
| vlm_transcript | **1.79** | 1.71 | 2.03 | 1.06 | 0.93 | 1.59 | 2.46 | 2.21 | 2.29 | 2.31 | 1.49 | 2.00 |

> ⚠️ 150-question stratified subset (TR/HL oversampled) — rows are NOT directly comparable to published full-set (1,998-question) numbers; use for internal method comparison, or re-run on the full set before placing in the same table as leaderboard entries.

### L2 dimensions + rollups

| Dimension | n | vlm_direct | vlm_transcript |
|-----------|---|---------|---------|
| CP | 17 | 1.59±0.00 / 1.59 | 1.71±0.00 / 1.71 |
| FP-S | 36 | 1.97±0.00 / 1.97 | 2.03±0.00 / 2.03 |
| FP-C | 17 | 1.12±0.00 / 1.12 | 1.06±0.00 / 1.06 |
| HL | 15 | 0.60±0.00 / 0.60 | 0.93±0.00 / 0.93 |
| LR | 11 | 2.46±0.00 / 2.46 | 2.46±0.00 / 2.46 |
| AR | 14 | 2.07±0.00 / 2.07 | 2.21±0.00 / 2.21 |
| RR | 14 | 2.07±0.00 / 2.07 | 2.29±0.00 / 2.29 |
| CSR | 13 | 2.38±0.00 / 2.38 | 2.31±0.00 / 2.31 |
| TR | 33 | 1.24±0.00 / 1.24 | 1.49±0.00 / 1.49 |
| **Perception** | 78 | 1.46±0.00 / 1.46 | 1.59±0.00 / 1.59 |
| **Reasoning** | 83 | 1.85±0.00 / 1.85 | 2.00±0.00 / 2.00 |
| **Overall** | 150 | 1.65±0.00 / 1.65 | 1.79±0.00 / 1.79 |

### 26 leaf capabilities

| Dimension | n | vlm_direct | vlm_transcript |
|-----------|---|---------|---------|
| Video Topic | 7 | 2.00±0.00 / 2.00 | 1.71±0.00 / 1.71 |
| Video Emotion | 4 | 1.25±0.00 / 1.25 | 1.50±0.00 / 1.50 |
| Video Scene | 6 | 1.33±0.00 / 1.33 | 1.83±0.00 / 1.83 |
| Video Style | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| OCR | 16 | 1.88±0.00 / 1.88 | 1.94±0.00 / 1.94 |
| Object Recognition | 6 | 2.67±0.00 / 2.67 | 2.83±0.00 / 2.83 |
| Attribute Recognition | 2 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Event Recognition | 8 | 0.75±0.00 / 0.75 | 1.00±0.00 / 1.00 |
| Human Motion | 3 | 2.33±0.00 / 2.33 | 1.67±0.00 / 1.67 |
| Counting | 3 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Human-object Interaction | 6 | 0.83±0.00 / 0.83 | 1.00±0.00 / 1.00 |
| Human Interaction | 12 | 1.33±0.00 / 1.33 | 1.17±0.00 / 1.17 |
| Hallucination | 15 | 0.60±0.00 / 0.60 | 0.93±0.00 / 0.93 |
| Structuralized Image-Text Understanding | 5 | 1.80±0.00 / 1.80 | 1.80±0.00 / 1.80 |
| Mathematical Calculation | 6 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Physical Property | 5 | 2.40±0.00 / 2.40 | 2.40±0.00 / 2.40 |
| Function Reasoning | 6 | 2.17±0.00 / 2.17 | 2.50±0.00 / 2.50 |
| Identity Reasoning | 3 | 1.33±0.00 / 1.33 | 1.33±0.00 / 1.33 |
| Natural Relation | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 |
| Physical Relation | 8 | 2.12±0.00 / 2.12 | 1.88±0.00 / 1.88 |
| Social Relation | 5 | 1.80±0.00 / 1.80 | 2.80±0.00 / 2.80 |
| Common Sense Reasoning | 13 | 2.38±0.00 / 2.38 | 2.31±0.00 / 2.31 |
| Counterfactual Reasoning | 8 | 1.38±0.00 / 1.38 | 1.50±0.00 / 1.50 |
| Causal Reasoning | 22 | 1.36±0.00 / 1.36 | 1.68±0.00 / 1.68 |
| Future Prediction | 4 | 0.75±0.00 / 0.75 | 0.75±0.00 / 0.75 |

## Per-Video Accuracy — MMBench-Video official (0-3)

| Video | vlm_direct | vlm_transcript |
|-------|------|------|
| 4jOk3ajqJ2s_processed.mp4 | 3.000 | 3.000 |
| Qnyb73rf7gM_processed.mp4 | 0.000 | 3.000 |
| dSHcCllTCzY.mp4 | 3.000 | 3.000 |
| HtFrFZN8ud4.mp4 | 0.000 | 0.000 |
| Pfq9tqX_r-4.mp4 | 2.500 | 3.000 |
| bVceDFUlkX4.mp4 | 0.000 | 2.000 |
| a1ZNeTpMve8.mp4 | 0.000 | 0.000 |
| cHazQV45SPs.mp4 | 0.000 | 0.000 |
| ebFwtm1hUWM.mp4 | 2.000 | 2.000 |
| DrQzaGncGmw.mp4 | 1.000 | 2.000 |
| -9mIKCYg2vU.mp4 | 2.000 | 2.000 |
| u0GSFSvWDG4.mp4 | 3.000 | 3.000 |
| Mylca_onT_I.mp4 | 0.000 | 2.000 |
| YGE5Q2wgfs8.mp4 | 0.000 | 0.000 |
| RWkKNcGmUI0.mp4 | 2.000 | 3.000 |
| 115amzVdV44_processed.mp4 | 2.000 | 3.000 |
| umlonbnm1Kk.mp4 | 0.000 | 0.000 |
| zmHB11-V3cs.mp4 | 3.000 | 3.000 |
| zRRm1Kpx5zQ.mp4 | 0.000 | 0.000 |
| rdQrwBVRzEg.mp4 | 1.000 | 1.000 |
| iBIGBcGo1rY.mp4 | 3.000 | 3.000 |
| 3jQ_toeu314.mp4 | 1.333 | 1.333 |
| UIoqKfO8RJw.mp4 | 2.000 | 2.000 |
| z3yqHiQxlhg.mp4 | 1.000 | 1.000 |
| vBOWe1WK0Ig.mp4 | 3.000 | 3.000 |
| SX2Ajdf4-34.mp4 | 1.000 | 0.000 |
| d2ohLXJBykM.mp4 | 3.000 | 3.000 |
| mSaQXWoUHm0.mp4 | 2.000 | 3.000 |
| rQt4Q-ML7U4.mp4 | 3.000 | 3.000 |
| mfBNcc33EGA.mp4 | 2.500 | 2.500 |
| BbARfF2Gf64.mp4 | 1.000 | 2.500 |
| py6OsO_WSqU.mp4 | 0.000 | 0.000 |
| SEdkof4g8Y8.mp4 | 1.000 | 1.000 |
| Eer_CfDgqhY.mp4 | 2.000 | 2.000 |
| 2Ja6H_up6TQ.mp4 | 3.000 | 3.000 |
| opf_wezZTic.mp4 | 2.000 | 1.000 |
| tn3bGHxJH_M.mp4 | 0.000 | 0.000 |
| zm5bL2v876s.mp4 | 2.000 | 2.000 |
| RnDYM-EBsXM.mp4 | 3.000 | 3.000 |
| no9Ajy0tabs.mp4 | 2.000 | 0.000 |
| ccz1kfkdo2o.mp4 | 3.000 | 3.000 |
| qyOpdQO2__c.mp4 | 0.000 | 0.000 |
| h70GdtAkEOw.mp4 | 0.000 | 0.000 |
| b5soe5g0igs.mp4 | 0.000 | 0.000 |
| nJYKKyZFqzU.mp4 | 3.000 | 3.000 |
| 3cs8S_urAXU.mp4 | 0.000 | 0.000 |
| pod4x5NJoYI.mp4 | 3.000 | 3.000 |
| Mng2me2TNro.mp4 | 0.000 | 0.000 |
| jF31ICvl1T8.mp4 | 3.000 | 3.000 |
| QVzeW1_hyHI.mp4 | 3.000 | 3.000 |
| fYP4SryI9L0.mp4 | 0.000 | 0.000 |
| _Zt1EuIEhvw_processed.mp4 | 0.000 | 0.000 |
| 2mYHGn_Pd5M_processed.mp4 | 0.000 | 1.000 |
| Q1cDKWToTGA.mp4 | 1.000 | 1.000 |
| 1zLgiOaOzNI.mp4 | 0.000 | 0.000 |
| bS1ePEZZCDY_processed.mp4 | 2.000 | 0.000 |
| 8dgyPRA86K0.mp4 | 3.000 | 3.000 |
| c_lFunATvhk.mp4 | 3.000 | 3.000 |
| RTSrYhD-Qk0.mp4 | 3.000 | 3.000 |
| dxE80fpImj8.mp4 | 3.000 | 1.000 |
| V_Hn6pT4M-Y.mp4 | 3.000 | 3.000 |
| biAFfW-uiKI.mp4 | 0.000 | 0.000 |
| 0018ybk0K-E.mp4 | 3.000 | 3.000 |
| 2zTwYcdW0Ew.mp4 | 3.000 | 3.000 |
| LOxxhecSHQM.mp4 | 0.500 | 0.500 |
| XnABXVhqXI0.mp4 | 3.000 | 3.000 |
| GgqhnkkJTp8.mp4 | 2.000 | 1.500 |
| 9uBbgltCs94.mp4 | 2.000 | 2.000 |
| zON0wDD7VJY.mp4 | 0.000 | 0.000 |
| GhABIaANJCY.mp4 | 2.000 | 2.000 |
| Zvoxf_W1ZvA.mp4 | 3.000 | 3.000 |
| zBv_fuKyg5E.mp4 | 3.000 | 3.000 |
| O-17kqjsiFc_processed.mp4 | 3.000 | 3.000 |
| 9OxNk-d1PNw.mp4 | 0.000 | 0.000 |
| e_iZaS00xds.mp4 | 0.000 | 0.000 |
| ZVl-Lm_XaTI.mp4 | 3.000 | 3.000 |
| QH7GaLx5JYc.mp4 | 0.000 | 2.000 |
| xUkqUL5bXSE.mp4 | 1.000 | 1.000 |
| HxxfnxOIzdo.mp4 | 0.000 | 0.000 |
| rDWzQ6lZNpY.mp4 | 3.000 | 3.000 |
| QKHPOzA9Ge0_processed.mp4 | 2.000 | 2.000 |
| rhkkCDTkcvI_processed.mp4 | 0.000 | 0.000 |
| ApNRpFOKQrA.mp4 | 0.000 | 0.000 |
| W8OzZa16vtE.mp4 | 3.000 | 3.000 |
| r7COWvxlN5g_processed.mp4 | 3.000 | 3.000 |
| 0eKi5V1IOi0.mp4 | 3.000 | 3.000 |
| hHZvUeAdzeI.mp4 | 0.000 | 0.000 |
| qfUZBKDh9BY_processed.mp4 | 3.000 | 3.000 |
| YGSKW5AVBjc.mp4 | 3.000 | 3.000 |
| WCT6xM9jyzA.mp4 | 2.000 | 2.000 |
| PU7j9UF4lpA.mp4 | 0.000 | 0.000 |
| BY3nBVbUYjI.mp4 | 3.000 | 3.000 |
| 4Gb0lotHA8E.mp4 | 0.000 | 1.000 |
| S2nBBMbjS8w.mp4 | 3.000 | 3.000 |
| AkaEnPxMla8.mp4 | 3.000 | 3.000 |
| bRpUauseTVw.mp4 | 0.000 | 1.000 |
| q01PqUubacA.mp4 | 0.000 | 1.500 |
| EpFKDzmMnao_processed.mp4 | 2.000 | 3.000 |
| LEHR8YQNm_Q.mp4 | 0.000 | 0.000 |
| hq7nFVTFukc.mp4 | 0.000 | 3.000 |
| 68191uKawYw.mp4 | 3.000 | 3.000 |
| 5phZ6-eHbqM.mp4 | 2.000 | 3.000 |
| l1uE_pBqnvE.mp4 | 3.000 | 3.000 |
| tnMr9abBX7k.mp4 | 0.000 | 3.000 |
| ZNRSHr3b4uA.mp4 | 0.000 | 0.000 |
| 66XwG1CLHuU.mp4 | 3.000 | 3.000 |
| 9HsKNFr7xmI.mp4 | 2.500 | 2.500 |
| TseT4C38UAg.mp4 | 2.000 | 2.000 |
| uO8v6bjwRdo.mp4 | 3.000 | 3.000 |
| BfemWi1SKdw.mp4 | 3.000 | 3.000 |
| Zh3Yz3PiXZw_processed.mp4 | 2.000 | 2.000 |
| M7OiIun5NfQ.mp4 | 1.000 | 2.000 |
| X3COFNPpdDc_processed.mp4 | 0.000 | 0.000 |
| B363bRgVUUA_processed.mp4 | 0.000 | 0.000 |
| bTG65BRLaRE_processed.mp4 | 0.000 | 0.000 |
| lWCA_3GLrCE_processed.mp4 | 1.000 | 1.000 |
| T2XOiCM0OOA_processed.mp4 | 3.000 | 3.000 |
| cTA2rkKp6qo_processed.mp4 | 3.000 | 3.000 |
| ddzjFNvpZhM.mp4 | 3.000 | 3.000 |
| yVkdfJ9PkRQ.mp4 | 3.000 | 3.000 |
| 5eNhS0oaLHo_processed.mp4 | 2.500 | 2.500 |
| 9j_HWkrSxzI_processed.mp4 | 3.000 | 3.000 |
| QkPJzK9SnTg.mp4 | 2.000 | 2.000 |
| Mwc4ePLjkQ8_processed.mp4 | 2.000 | 1.000 |
| WydM_QmW1ec.mp4 | 3.000 | 3.000 |
| vNhORnwcQcU_processed.mp4 | 3.000 | 3.000 |
| IFQ9zQekRio_processed.mp4 | 0.000 | 2.000 |
| L8luXQhnAGk.mp4 | 2.000 | 2.000 |
| zXR93P8EnxM_processed.mp4 | 1.000 | 1.000 |
| khXSmQHenSk_processed.mp4 | 0.000 | 0.000 |
| kiwy_nV-hxE.mp4 | 0.000 | 0.000 |
| b9DW-tHrQB8.mp4 | 2.000 | 2.000 |
| G4DPefY6-NM.mp4 | 2.500 | 1.500 |
| 0luoGkddtYw_processed.mp4 | 3.000 | 3.000 |
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