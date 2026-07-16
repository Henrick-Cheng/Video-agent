# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 3  |  Generated: 2026-07-17 02:11

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|------|
| **agent_v2** | 1.984 ± 0.101 | 1.7 | 0.0 | 3.6 | 10546 | 6108 | 16655 |
| **vlm_transcript** | 1.727 ± 0.020 | — | 0.0 | 8.0 | 7299 | — | 7299 |
| **vlm_direct** | 1.478 ± 0.025 | — | 0.0 | 8.0 | 6748 | — | 6748 |

## MMBench-Video Official Rating (multi-label, 0-3)

> VLMEvalKit `get_dimension_rating` semantics: each question counts toward **every** dimension it is tagged with (a question can appear in several rows). Cell = `all / valid` mean: *all* scores judge failures as 0 (official leaderboard variant); *valid* excludes them (`(vN)` marks buckets with failures). ± std over trials is an extension over the official single-run protocol. n = questions per bucket.

### Paper-style summary (Table-3 layout of the MMBench-Video paper)

| Model | Overall Mean | CP | FP-S | FP-C | HL | *P. Mean* | LR | AR | RR | CSR | TR | *R. Mean* |
|-------|------|----|----|----|----|----|----|----|----|----|----|----|----|
| agent_v2 | **1.98** | 2.25 | 2.06 | 1.39 | 2.42 | 2.06 | 2.21 | 2.14 | 2.00 | 2.23 | 1.68 | 1.96 |
| vlm_transcript | **1.73** | 1.63 | 1.73 | 0.78 | 1.04 | 1.40 | 1.85 | 2.50 | 2.12 | 2.36 | 1.88 | 2.09 |
| vlm_direct | **1.48** | 1.57 | 1.55 | 0.61 | 0.62 | 1.22 | 1.61 | 2.33 | 1.76 | 2.31 | 1.51 | 1.82 |

> ⚠️ 150-question stratified subset (TR/HL oversampled) — rows are NOT directly comparable to published full-set (1,998-question) numbers; use for internal method comparison, or re-run on the full set before placing in the same table as leaderboard entries.

### L2 dimensions + rollups

| Dimension | n | agent_v2 | vlm_transcript | vlm_direct |
|-----------|---|---------|---------|---------|
| CP | 17 | 2.25±0.10 / 2.25 | 1.63±0.03 / 1.63 | 1.57±0.06 / 1.57 |
| FP-S | 36 | 2.06±0.16 / 2.06 | 1.73±0.04 / 1.73 | 1.55±0.01 / 1.55 |
| FP-C | 17 | 1.39±0.12 / 1.39 | 0.78±0.06 / 0.78 | 0.61±0.06 / 0.61 |
| HL | 15 | 2.42±0.19 / 2.42 | 1.04±0.14 / 1.04 | 0.62±0.13 / 0.62 |
| LR | 11 | 2.21±0.30 / 2.21 | 1.85±0.04 / 1.85 | 1.61±0.04 / 1.61 |
| AR | 14 | 2.14±0.10 / 2.14 | 2.50±0.00 / 2.50 | 2.33±0.03 / 2.33 |
| RR | 14 | 2.00±0.12 / 2.00 | 2.12±0.03 / 2.12 | 1.76±0.03 / 1.76 |
| CSR | 13 | 2.23±0.13 / 2.23 | 2.36±0.04 / 2.36 | 2.31±0.00 / 2.31 |
| TR | 33 | 1.68±0.14 / 1.68 | 1.88±0.09 / 1.88 | 1.51±0.03 / 1.51 |
| **Perception** | 78 | 2.06±0.12 / 2.06 | 1.40±0.04 / 1.40 | 1.22±0.05 / 1.22 |
| **Reasoning** | 83 | 1.96±0.13 / 1.96 | 2.09±0.03 / 2.09 | 1.82±0.01 / 1.82 |
| **Overall** | 150 | 1.98±0.10 / 1.98 | 1.73±0.02 / 1.73 | 1.48±0.03 / 1.48 |

### 26 leaf capabilities

| Dimension | n | agent_v2 | vlm_transcript | vlm_direct |
|-----------|---|---------|---------|---------|
| Video Topic | 7 | 2.48±0.18 / 2.48 | 1.57±0.00 / 1.57 | 1.86±0.12 / 1.86 |
| Video Emotion | 4 | 2.00±0.35 / 2.00 | 1.42±0.12 / 1.42 | 1.83±0.12 / 1.83 |
| Video Scene | 6 | 2.17±0.24 / 2.17 | 1.83±0.00 / 1.83 | 1.06±0.08 / 1.06 |
| Video Style | 1 | 3.00±0.00 / 3.00 | 1.67±0.47 / 1.67 | 1.67±0.47 / 1.67 |
| OCR | 16 | 2.31±0.15 / 2.31 | 2.04±0.06 / 2.04 | 1.75±0.00 / 1.75 |
| Object Recognition | 6 | 1.83±0.24 / 1.83 | 1.50±0.00 / 1.50 | 1.33±0.00 / 1.33 |
| Attribute Recognition | 2 | 3.00±0.00 / 3.00 | 1.50±0.00 / 1.50 | 1.50±0.00 / 1.50 |
| Event Recognition | 8 | 1.17±0.42 / 1.17 | 0.96±0.06 / 0.96 | 0.83±0.06 / 0.83 |
| Human Motion | 3 | 1.89±0.31 / 1.89 | 1.33±0.00 / 1.33 | 1.33±0.00 / 1.33 |
| Counting | 3 | 3.00±0.00 / 3.00 | 2.00±0.00 / 2.00 | 2.00±0.00 / 2.00 |
| Human-object Interaction | 6 | 0.89±0.08 / 0.89 | 0.89±0.08 / 0.89 | 0.50±0.14 / 0.50 |
| Human Interaction | 12 | 1.67±0.18 / 1.67 | 0.83±0.07 / 0.83 | 0.72±0.04 / 0.72 |
| Hallucination | 15 | 2.42±0.19 / 2.42 | 1.04±0.14 / 1.04 | 0.62±0.13 / 0.62 |
| Structuralized Image-Text Understanding | 5 | 2.07±0.25 / 2.07 | 2.27±0.09 / 2.27 | 2.33±0.09 / 2.33 |
| Mathematical Calculation | 6 | 2.33±0.47 / 2.33 | 1.50±0.00 / 1.50 | 1.00±0.00 / 1.00 |
| Physical Property | 5 | 2.07±0.09 / 2.07 | 2.60±0.00 / 2.60 | 2.27±0.09 / 2.27 |
| Function Reasoning | 6 | 2.44±0.08 / 2.44 | 2.17±0.00 / 2.17 | 2.17±0.00 / 2.17 |
| Identity Reasoning | 3 | 1.67±0.27 / 1.67 | 3.00±0.00 / 3.00 | 2.78±0.16 / 2.78 |
| Natural Relation | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 | 1.00±0.00 / 1.00 |
| Physical Relation | 8 | 2.21±0.06 / 2.21 | 2.08±0.06 / 2.08 | 2.08±0.06 / 2.08 |
| Social Relation | 5 | 1.47±0.25 / 1.47 | 2.00±0.00 / 2.00 | 1.40±0.00 / 1.40 |
| Common Sense Reasoning | 13 | 2.23±0.13 / 2.23 | 2.36±0.04 / 2.36 | 2.31±0.00 / 2.31 |
| Counterfactual Reasoning | 8 | 1.83±0.24 / 1.83 | 1.71±0.06 / 1.71 | 1.46±0.16 / 1.46 |
| Causal Reasoning | 22 | 1.77±0.06 / 1.77 | 2.08±0.09 / 2.08 | 1.65±0.02 / 1.65 |
| Future Prediction | 4 | 1.17±0.31 / 1.17 | 1.42±0.12 / 1.42 | 1.25±0.00 / 1.25 |

## Per-Video Accuracy — MMBench-Video official (0-3)

| Video | agent_v2 | vlm_transcript | vlm_direct |
|-------|------|------|------|
| 4jOk3ajqJ2s_processed.mp4 | 3.000 | 3.000 | 3.000 |
| Qnyb73rf7gM_processed.mp4 | 3.000 | 0.000 | 0.000 |
| dSHcCllTCzY.mp4 | 1.333 | 3.000 | 3.000 |
| HtFrFZN8ud4.mp4 | 1.000 | 0.000 | 0.000 |
| Pfq9tqX_r-4.mp4 | 3.000 | 2.500 | 1.000 |
| bVceDFUlkX4.mp4 | 0.667 | 1.000 | 1.000 |
| a1ZNeTpMve8.mp4 | 3.000 | 0.000 | 0.000 |
| cHazQV45SPs.mp4 | 3.000 | 3.000 | 3.000 |
| ebFwtm1hUWM.mp4 | 1.000 | 0.000 | 0.000 |
| DrQzaGncGmw.mp4 | 0.333 | 1.000 | 0.667 |
| -9mIKCYg2vU.mp4 | 1.667 | 2.333 | 2.333 |
| u0GSFSvWDG4.mp4 | 1.000 | 0.333 | 0.000 |
| Mylca_onT_I.mp4 | 3.000 | 0.333 | 0.333 |
| YGE5Q2wgfs8.mp4 | 3.000 | 2.000 | 0.000 |
| RWkKNcGmUI0.mp4 | 3.000 | 2.333 | 3.000 |
| 115amzVdV44_processed.mp4 | 2.333 | 2.667 | 2.333 |
| umlonbnm1Kk.mp4 | 1.000 | 1.333 | 1.000 |
| zmHB11-V3cs.mp4 | 3.000 | 3.000 | 1.000 |
| zRRm1Kpx5zQ.mp4 | 1.000 | 0.000 | 0.000 |
| rdQrwBVRzEg.mp4 | 2.000 | 2.000 | 2.000 |
| iBIGBcGo1rY.mp4 | 3.000 | 1.667 | 1.667 |
| 3jQ_toeu314.mp4 | 1.111 | 2.222 | 1.667 |
| UIoqKfO8RJw.mp4 | 0.000 | 0.000 | 0.000 |
| z3yqHiQxlhg.mp4 | 1.167 | 1.833 | 0.833 |
| vBOWe1WK0Ig.mp4 | 3.000 | 3.000 | 1.000 |
| SX2Ajdf4-34.mp4 | 0.667 | 1.167 | 0.333 |
| d2ohLXJBykM.mp4 | 3.000 | 3.000 | 2.667 |
| mSaQXWoUHm0.mp4 | 3.000 | 3.000 | 1.000 |
| rQt4Q-ML7U4.mp4 | 3.000 | 2.000 | 2.000 |
| mfBNcc33EGA.mp4 | 3.000 | 3.000 | 2.833 |
| BbARfF2Gf64.mp4 | 3.000 | 2.667 | 2.333 |
| py6OsO_WSqU.mp4 | 0.000 | 0.000 | 0.000 |
| SEdkof4g8Y8.mp4 | 2.000 | 1.000 | 1.000 |
| Eer_CfDgqhY.mp4 | 1.333 | 0.000 | 0.000 |
| 2Ja6H_up6TQ.mp4 | 3.000 | 2.667 | 2.333 |
| opf_wezZTic.mp4 | 0.667 | 1.000 | 1.667 |
| tn3bGHxJH_M.mp4 | 2.000 | 0.000 | 1.333 |
| zm5bL2v876s.mp4 | 1.667 | 1.000 | 2.000 |
| RnDYM-EBsXM.mp4 | 3.000 | 3.000 | 3.000 |
| no9Ajy0tabs.mp4 | 1.333 | 2.000 | 2.333 |
| ccz1kfkdo2o.mp4 | 3.000 | 3.000 | 3.000 |
| qyOpdQO2__c.mp4 | 1.000 | 0.000 | 0.000 |
| h70GdtAkEOw.mp4 | 0.000 | 0.000 | 0.000 |
| b5soe5g0igs.mp4 | 2.000 | 0.000 | 0.000 |
| nJYKKyZFqzU.mp4 | 3.000 | 3.000 | 3.000 |
| 3cs8S_urAXU.mp4 | 3.000 | 3.000 | 0.000 |
| pod4x5NJoYI.mp4 | 3.000 | 3.000 | 3.000 |
| Mng2me2TNro.mp4 | 3.000 | 0.000 | 0.000 |
| jF31ICvl1T8.mp4 | 0.000 | 3.000 | 3.000 |
| QVzeW1_hyHI.mp4 | 2.000 | 1.333 | 0.000 |
| fYP4SryI9L0.mp4 | 0.667 | 1.000 | 1.000 |
| _Zt1EuIEhvw_processed.mp4 | 0.667 | 0.333 | 0.000 |
| 2mYHGn_Pd5M_processed.mp4 | 0.000 | 1.667 | 1.000 |
| Q1cDKWToTGA.mp4 | 2.333 | 1.000 | 0.667 |
| 1zLgiOaOzNI.mp4 | 2.667 | 0.333 | 1.333 |
| bS1ePEZZCDY_processed.mp4 | 1.333 | 1.000 | 1.000 |
| 8dgyPRA86K0.mp4 | 3.000 | 3.000 | 3.000 |
| c_lFunATvhk.mp4 | 3.000 | 3.000 | 3.000 |
| RTSrYhD-Qk0.mp4 | 3.000 | 3.000 | 3.000 |
| dxE80fpImj8.mp4 | 1.333 | 0.333 | 0.333 |
| V_Hn6pT4M-Y.mp4 | 3.000 | 3.000 | 3.000 |
| biAFfW-uiKI.mp4 | 1.000 | 1.000 | 0.667 |
| 0018ybk0K-E.mp4 | 3.000 | 3.000 | 0.000 |
| 2zTwYcdW0Ew.mp4 | 3.000 | 0.000 | 0.000 |
| LOxxhecSHQM.mp4 | 1.167 | 0.333 | 0.000 |
| XnABXVhqXI0.mp4 | 3.000 | 3.000 | 3.000 |
| GgqhnkkJTp8.mp4 | 2.167 | 0.500 | 0.500 |
| 9uBbgltCs94.mp4 | 2.333 | 1.667 | 1.000 |
| zON0wDD7VJY.mp4 | 0.333 | 1.000 | 0.667 |
| GhABIaANJCY.mp4 | 2.000 | 1.000 | 1.333 |
| Zvoxf_W1ZvA.mp4 | 3.000 | 1.667 | 2.000 |
| zBv_fuKyg5E.mp4 | 2.667 | 3.000 | 3.000 |
| O-17kqjsiFc_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 9OxNk-d1PNw.mp4 | 2.000 | 1.000 | 1.000 |
| e_iZaS00xds.mp4 | 2.333 | 1.333 | 2.000 |
| ZVl-Lm_XaTI.mp4 | 3.000 | 3.000 | 3.000 |
| QH7GaLx5JYc.mp4 | 2.333 | 0.000 | 0.000 |
| xUkqUL5bXSE.mp4 | 2.000 | 2.000 | 0.000 |
| HxxfnxOIzdo.mp4 | 0.000 | 0.000 | 0.000 |
| rDWzQ6lZNpY.mp4 | 0.000 | 0.000 | 0.000 |
| QKHPOzA9Ge0_processed.mp4 | 2.000 | 3.000 | 3.000 |
| rhkkCDTkcvI_processed.mp4 | 2.000 | 0.000 | 0.000 |
| ApNRpFOKQrA.mp4 | 0.667 | 0.000 | 0.000 |
| W8OzZa16vtE.mp4 | 3.000 | 3.000 | 3.000 |
| r7COWvxlN5g_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 0eKi5V1IOi0.mp4 | 3.000 | 3.000 | 3.000 |
| hHZvUeAdzeI.mp4 | 3.000 | 0.000 | 0.000 |
| qfUZBKDh9BY_processed.mp4 | 3.000 | 3.000 | 3.000 |
| YGSKW5AVBjc.mp4 | 3.000 | 0.000 | 0.000 |
| WCT6xM9jyzA.mp4 | 3.000 | 3.000 | 2.667 |
| PU7j9UF4lpA.mp4 | 1.000 | 1.333 | 2.000 |
| BY3nBVbUYjI.mp4 | 1.000 | 3.000 | 3.000 |
| 4Gb0lotHA8E.mp4 | 1.667 | 0.667 | 2.000 |
| S2nBBMbjS8w.mp4 | 3.000 | 3.000 | 3.000 |
| AkaEnPxMla8.mp4 | 2.000 | 3.000 | 3.000 |
| bRpUauseTVw.mp4 | 1.333 | 1.000 | 1.000 |
| q01PqUubacA.mp4 | 2.167 | 1.000 | 0.500 |
| EpFKDzmMnao_processed.mp4 | 3.000 | 3.000 | 2.000 |
| LEHR8YQNm_Q.mp4 | 0.000 | 1.000 | 0.667 |
| hq7nFVTFukc.mp4 | 3.000 | 3.000 | 0.667 |
| 68191uKawYw.mp4 | 3.000 | 3.000 | 3.000 |
| 5phZ6-eHbqM.mp4 | 2.333 | 3.000 | 2.000 |
| l1uE_pBqnvE.mp4 | 0.667 | 3.000 | 0.000 |
| tnMr9abBX7k.mp4 | 0.000 | 0.000 | 0.000 |
| ZNRSHr3b4uA.mp4 | 0.000 | 1.000 | 1.000 |
| 66XwG1CLHuU.mp4 | 2.667 | 3.000 | 3.000 |
| 9HsKNFr7xmI.mp4 | 1.500 | 3.000 | 3.000 |
| TseT4C38UAg.mp4 | 1.000 | 0.000 | 0.000 |
| uO8v6bjwRdo.mp4 | 2.000 | 0.000 | 0.000 |
| BfemWi1SKdw.mp4 | 2.000 | 1.000 | 1.000 |
| Zh3Yz3PiXZw_processed.mp4 | 2.667 | 3.000 | 2.667 |
| M7OiIun5NfQ.mp4 | 0.667 | 1.333 | 1.000 |
| X3COFNPpdDc_processed.mp4 | 1.000 | 0.667 | 0.333 |
| B363bRgVUUA_processed.mp4 | 0.333 | 0.667 | 0.333 |
| bTG65BRLaRE_processed.mp4 | 2.000 | 0.000 | 0.000 |
| lWCA_3GLrCE_processed.mp4 | 1.000 | 0.000 | 0.000 |
| T2XOiCM0OOA_processed.mp4 | 3.000 | 3.000 | 3.000 |
| cTA2rkKp6qo_processed.mp4 | 3.000 | 3.000 | 3.000 |
| ddzjFNvpZhM.mp4 | 3.000 | 3.000 | 3.000 |
| yVkdfJ9PkRQ.mp4 | 0.000 | 3.000 | 1.000 |
| 5eNhS0oaLHo_processed.mp4 | 3.000 | 3.000 | 2.833 |
| 9j_HWkrSxzI_processed.mp4 | 3.000 | 3.000 | 3.000 |
| QkPJzK9SnTg.mp4 | 2.000 | 1.000 | 1.000 |
| Mwc4ePLjkQ8_processed.mp4 | 2.000 | 2.000 | 3.000 |
| WydM_QmW1ec.mp4 | 2.333 | 3.000 | 3.000 |
| vNhORnwcQcU_processed.mp4 | 3.000 | 3.000 | 1.000 |
| IFQ9zQekRio_processed.mp4 | 1.667 | 2.000 | 2.000 |
| L8luXQhnAGk.mp4 | 0.000 | 0.000 | 0.000 |
| zXR93P8EnxM_processed.mp4 | 1.333 | 1.667 | 2.000 |
| khXSmQHenSk_processed.mp4 | 3.000 | 0.000 | 0.000 |
| kiwy_nV-hxE.mp4 | 2.333 | 3.000 | 2.667 |
| b9DW-tHrQB8.mp4 | 2.667 | 3.000 | 3.000 |
| G4DPefY6-NM.mp4 | 1.500 | 2.333 | 2.500 |
| 0luoGkddtYw_processed.mp4 | 3.000 | 3.000 | 3.000 |
| HRe90ySP38U_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 9-r4VLHQRlM_processed.mp4 | 2.667 | 2.000 | 2.000 |

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
- Each method ran 3 independent trials; mean ± std reported over trials