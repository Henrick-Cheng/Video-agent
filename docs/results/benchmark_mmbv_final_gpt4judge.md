# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 3  |  Generated: 2026-07-17 02:38

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|------|
| **agent_v2** | 1.978 ± 0.097 | 1.7 | 0.0 | 3.6 | 10546 | 6108 | 16655 |
| **vlm_transcript** | 1.713 ± 0.019 | — | 0.0 | 8.0 | 7299 | — | 7299 |
| **vlm_direct** | 1.491 ± 0.019 | — | 0.0 | 8.0 | 6748 | — | 6748 |

## MMBench-Video Official Rating (multi-label, 0-3)

> VLMEvalKit `get_dimension_rating` semantics: each question counts toward **every** dimension it is tagged with (a question can appear in several rows). Cell = `all / valid` mean: *all* scores judge failures as 0 (official leaderboard variant); *valid* excludes them (`(vN)` marks buckets with failures). ± std over trials is an extension over the official single-run protocol. n = questions per bucket.

### Paper-style summary (Table-3 layout of the MMBench-Video paper)

| Model | Overall Mean | CP | FP-S | FP-C | HL | *P. Mean* | LR | AR | RR | CSR | TR | *R. Mean* |
|-------|------|----|----|----|----|----|----|----|----|----|----|----|----|
| agent_v2 | **1.98** | 2.18 | 2.08 | 1.47 | 2.29 | 2.04 | 2.18 | 2.07 | 2.07 | 2.21 | 1.74 | 1.98 |
| vlm_transcript | **1.71** | 1.78 | 1.81 | 0.90 | 0.78 | 1.42 | 1.73 | 2.50 | 2.12 | 2.28 | 1.87 | 2.07 |
| vlm_direct | **1.49** | 1.53 | 1.64 | 0.77 | 0.64 | 1.28 | 1.39 | 2.21 | 1.81 | 2.26 | 1.52 | 1.79 |

> ⚠️ 150-question stratified subset (TR/HL oversampled) — rows are NOT directly comparable to published full-set (1,998-question) numbers; use for internal method comparison, or re-run on the full set before placing in the same table as leaderboard entries.

### L2 dimensions + rollups

| Dimension | n | agent_v2 | vlm_transcript | vlm_direct |
|-----------|---|---------|---------|---------|
| CP | 17 | 2.18±0.08 / 2.18 | 1.78±0.06 / 1.78 | 1.53±0.08 / 1.53 |
| FP-S | 36 | 2.08±0.15 / 2.08 | 1.81±0.02 / 1.81 | 1.64±0.06 / 1.64 |
| FP-C | 17 | 1.47±0.10 / 1.47 | 0.90±0.06 / 0.90 | 0.77±0.05 / 0.77 |
| HL | 15 | 2.29±0.08 / 2.29 | 0.78±0.03 / 0.78 | 0.64±0.03 / 0.64 |
| LR | 11 | 2.18±0.22 / 2.18 | 1.73±0.15 / 1.73 | 1.39±0.04 / 1.39 |
| AR | 14 | 2.07±0.17 / 2.07 | 2.50±0.06 / 2.50 | 2.21±0.10 / 2.21 |
| RR | 14 | 2.07±0.15 / 2.07 | 2.12±0.09 / 2.12 | 1.81±0.03 / 1.81 |
| CSR | 13 | 2.21±0.13 / 2.21 | 2.28±0.04 / 2.28 | 2.26±0.04 / 2.26 |
| TR | 33 | 1.74±0.10 / 1.74 | 1.87±0.05 / 1.87 | 1.52±0.01 / 1.52 |
| **Perception** | 78 | 2.04±0.09 / 2.04 | 1.42±0.02 / 1.42 | 1.28±0.06 / 1.28 |
| **Reasoning** | 83 | 1.98±0.12 / 1.98 | 2.07±0.02 / 2.07 | 1.79±0.02 / 1.79 |
| **Overall** | 150 | 1.98±0.10 / 1.98 | 1.71±0.02 / 1.71 | 1.49±0.02 / 1.49 |

### 26 leaf capabilities

| Dimension | n | agent_v2 | vlm_transcript | vlm_direct |
|-----------|---|---------|---------|---------|
| Video Topic | 7 | 2.38±0.14 / 2.38 | 1.76±0.07 / 1.76 | 1.76±0.14 / 1.76 |
| Video Emotion | 4 | 1.75±0.41 / 1.75 | 1.50±0.00 / 1.50 | 1.50±0.00 / 1.50 |
| Video Scene | 6 | 2.22±0.28 / 2.22 | 2.00±0.14 / 2.00 | 1.28±0.08 / 1.28 |
| Video Style | 1 | 3.00±0.00 / 3.00 | 1.33±0.47 / 1.33 | 1.33±0.47 / 1.33 |
| OCR | 16 | 2.31±0.15 / 2.31 | 2.00±0.05 / 2.00 | 1.69±0.05 / 1.69 |
| Object Recognition | 6 | 1.78±0.28 / 1.78 | 1.50±0.00 / 1.50 | 1.39±0.08 / 1.39 |
| Attribute Recognition | 2 | 3.00±0.00 / 3.00 | 1.50±0.00 / 1.50 | 1.50±0.00 / 1.50 |
| Event Recognition | 8 | 1.21±0.31 / 1.21 | 1.33±0.06 / 1.33 | 1.21±0.16 / 1.21 |
| Human Motion | 3 | 2.22±0.16 / 2.22 | 1.44±0.16 / 1.44 | 1.67±0.00 / 1.67 |
| Counting | 3 | 3.00±0.00 / 3.00 | 2.00±0.00 / 2.00 | 2.00±0.00 / 2.00 |
| Human-object Interaction | 6 | 0.89±0.08 / 0.89 | 0.89±0.08 / 0.89 | 0.72±0.16 / 0.72 |
| Human Interaction | 12 | 1.78±0.21 / 1.78 | 0.97±0.10 / 0.97 | 0.86±0.04 / 0.86 |
| Hallucination | 15 | 2.29±0.08 / 2.29 | 0.78±0.03 / 0.78 | 0.64±0.03 / 0.64 |
| Structuralized Image-Text Understanding | 5 | 2.20±0.28 / 2.20 | 2.33±0.19 / 2.33 | 2.07±0.09 / 2.07 |
| Mathematical Calculation | 6 | 2.17±0.47 / 2.17 | 1.22±0.16 / 1.22 | 0.83±0.00 / 0.83 |
| Physical Property | 5 | 2.20±0.28 / 2.20 | 2.47±0.09 / 2.47 | 2.13±0.09 / 2.13 |
| Function Reasoning | 6 | 2.06±0.21 / 2.06 | 2.33±0.00 / 2.33 | 2.06±0.16 / 2.06 |
| Identity Reasoning | 3 | 1.89±0.31 / 1.89 | 2.89±0.16 / 2.89 | 2.67±0.00 / 2.67 |
| Natural Relation | 1 | 3.00±0.00 / 3.00 | 3.00±0.00 / 3.00 | 1.67±0.47 / 1.67 |
| Physical Relation | 8 | 2.42±0.24 / 2.42 | 2.08±0.16 / 2.08 | 2.08±0.06 / 2.08 |
| Social Relation | 5 | 1.33±0.09 / 1.33 | 2.00±0.00 / 2.00 | 1.40±0.00 / 1.40 |
| Common Sense Reasoning | 13 | 2.21±0.13 / 2.21 | 2.28±0.04 / 2.28 | 2.26±0.04 / 2.26 |
| Counterfactual Reasoning | 8 | 2.08±0.16 / 2.08 | 1.67±0.12 / 1.67 | 1.50±0.00 / 1.50 |
| Causal Reasoning | 22 | 1.79±0.06 / 1.79 | 2.12±0.04 / 2.12 | 1.67±0.02 / 1.67 |
| Future Prediction | 4 | 1.08±0.31 / 1.08 | 1.17±0.12 / 1.17 | 1.17±0.12 / 1.17 |

## Per-Video Accuracy — MMBench-Video official (0-3)

| Video | agent_v2 | vlm_transcript | vlm_direct |
|-------|------|------|------|
| 4jOk3ajqJ2s_processed.mp4 | 3.000 | 2.667 | 2.667 |
| Qnyb73rf7gM_processed.mp4 | 3.000 | 0.000 | 0.667 |
| dSHcCllTCzY.mp4 | 0.667 | 3.000 | 3.000 |
| HtFrFZN8ud4.mp4 | 1.000 | 0.000 | 0.000 |
| Pfq9tqX_r-4.mp4 | 3.000 | 2.500 | 0.833 |
| bVceDFUlkX4.mp4 | 0.333 | 1.000 | 1.000 |
| a1ZNeTpMve8.mp4 | 3.000 | 0.000 | 0.000 |
| cHazQV45SPs.mp4 | 3.000 | 3.000 | 3.000 |
| ebFwtm1hUWM.mp4 | 1.000 | 0.000 | 0.000 |
| DrQzaGncGmw.mp4 | 0.333 | 1.000 | 1.000 |
| -9mIKCYg2vU.mp4 | 2.000 | 3.000 | 3.000 |
| u0GSFSvWDG4.mp4 | 0.000 | 0.000 | 0.000 |
| Mylca_onT_I.mp4 | 3.000 | 1.000 | 0.333 |
| YGE5Q2wgfs8.mp4 | 3.000 | 0.667 | 0.000 |
| RWkKNcGmUI0.mp4 | 3.000 | 1.333 | 2.000 |
| 115amzVdV44_processed.mp4 | 1.667 | 2.000 | 2.333 |
| umlonbnm1Kk.mp4 | 1.000 | 1.333 | 1.333 |
| zmHB11-V3cs.mp4 | 2.333 | 1.000 | 1.000 |
| zRRm1Kpx5zQ.mp4 | 1.000 | 0.000 | 0.000 |
| rdQrwBVRzEg.mp4 | 2.000 | 2.000 | 2.000 |
| iBIGBcGo1rY.mp4 | 3.000 | 1.333 | 1.333 |
| 3jQ_toeu314.mp4 | 1.000 | 2.222 | 2.000 |
| UIoqKfO8RJw.mp4 | 0.000 | 1.000 | 1.000 |
| z3yqHiQxlhg.mp4 | 1.167 | 1.500 | 0.667 |
| vBOWe1WK0Ig.mp4 | 3.000 | 3.000 | 1.000 |
| SX2Ajdf4-34.mp4 | 0.833 | 1.000 | 0.333 |
| d2ohLXJBykM.mp4 | 3.000 | 2.333 | 2.333 |
| mSaQXWoUHm0.mp4 | 3.000 | 3.000 | 1.000 |
| rQt4Q-ML7U4.mp4 | 2.333 | 2.000 | 2.000 |
| mfBNcc33EGA.mp4 | 3.000 | 2.667 | 2.500 |
| BbARfF2Gf64.mp4 | 3.000 | 2.500 | 1.833 |
| py6OsO_WSqU.mp4 | 1.000 | 0.000 | 0.667 |
| SEdkof4g8Y8.mp4 | 1.000 | 1.667 | 2.000 |
| Eer_CfDgqhY.mp4 | 2.667 | 0.333 | 1.000 |
| 2Ja6H_up6TQ.mp4 | 3.000 | 2.667 | 2.333 |
| opf_wezZTic.mp4 | 1.000 | 1.000 | 1.000 |
| tn3bGHxJH_M.mp4 | 2.333 | 0.000 | 1.000 |
| zm5bL2v876s.mp4 | 1.667 | 1.333 | 2.000 |
| RnDYM-EBsXM.mp4 | 3.000 | 3.000 | 3.000 |
| no9Ajy0tabs.mp4 | 2.000 | 2.667 | 2.667 |
| ccz1kfkdo2o.mp4 | 3.000 | 3.000 | 3.000 |
| qyOpdQO2__c.mp4 | 0.000 | 0.000 | 0.000 |
| h70GdtAkEOw.mp4 | 0.000 | 0.000 | 0.000 |
| b5soe5g0igs.mp4 | 1.667 | 0.000 | 0.000 |
| nJYKKyZFqzU.mp4 | 3.000 | 3.000 | 3.000 |
| 3cs8S_urAXU.mp4 | 3.000 | 1.000 | 0.000 |
| pod4x5NJoYI.mp4 | 3.000 | 3.000 | 3.000 |
| Mng2me2TNro.mp4 | 3.000 | 0.000 | 0.000 |
| jF31ICvl1T8.mp4 | 0.000 | 3.000 | 3.000 |
| QVzeW1_hyHI.mp4 | 2.667 | 1.667 | 0.000 |
| fYP4SryI9L0.mp4 | 2.000 | 2.000 | 2.000 |
| _Zt1EuIEhvw_processed.mp4 | 1.000 | 1.000 | 1.000 |
| 2mYHGn_Pd5M_processed.mp4 | 0.000 | 1.667 | 1.000 |
| Q1cDKWToTGA.mp4 | 1.667 | 0.833 | 0.833 |
| 1zLgiOaOzNI.mp4 | 2.667 | 1.000 | 1.333 |
| bS1ePEZZCDY_processed.mp4 | 1.000 | 1.000 | 1.000 |
| 8dgyPRA86K0.mp4 | 2.667 | 2.667 | 3.000 |
| c_lFunATvhk.mp4 | 3.000 | 3.000 | 3.000 |
| RTSrYhD-Qk0.mp4 | 3.000 | 3.000 | 3.000 |
| dxE80fpImj8.mp4 | 1.667 | 1.000 | 1.000 |
| V_Hn6pT4M-Y.mp4 | 3.000 | 3.000 | 3.000 |
| biAFfW-uiKI.mp4 | 1.000 | 0.000 | 0.000 |
| 0018ybk0K-E.mp4 | 3.000 | 3.000 | 0.667 |
| 2zTwYcdW0Ew.mp4 | 3.000 | 0.000 | 0.000 |
| LOxxhecSHQM.mp4 | 1.000 | 0.333 | 0.000 |
| XnABXVhqXI0.mp4 | 3.000 | 3.000 | 3.000 |
| GgqhnkkJTp8.mp4 | 2.000 | 1.000 | 0.500 |
| 9uBbgltCs94.mp4 | 2.000 | 2.667 | 1.000 |
| zON0wDD7VJY.mp4 | 0.333 | 0.667 | 0.667 |
| GhABIaANJCY.mp4 | 1.667 | 1.000 | 1.000 |
| Zvoxf_W1ZvA.mp4 | 3.000 | 1.333 | 2.000 |
| zBv_fuKyg5E.mp4 | 3.000 | 3.000 | 3.000 |
| O-17kqjsiFc_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 9OxNk-d1PNw.mp4 | 2.000 | 1.000 | 0.000 |
| e_iZaS00xds.mp4 | 3.000 | 2.333 | 2.000 |
| ZVl-Lm_XaTI.mp4 | 3.000 | 3.000 | 3.000 |
| QH7GaLx5JYc.mp4 | 2.667 | 0.333 | 0.667 |
| xUkqUL5bXSE.mp4 | 2.000 | 2.000 | 0.000 |
| HxxfnxOIzdo.mp4 | 0.000 | 1.000 | 0.667 |
| rDWzQ6lZNpY.mp4 | 0.000 | 0.000 | 0.000 |
| QKHPOzA9Ge0_processed.mp4 | 2.000 | 3.000 | 3.000 |
| rhkkCDTkcvI_processed.mp4 | 2.000 | 0.000 | 0.000 |
| ApNRpFOKQrA.mp4 | 0.333 | 0.000 | 0.000 |
| W8OzZa16vtE.mp4 | 3.000 | 3.000 | 3.000 |
| r7COWvxlN5g_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 0eKi5V1IOi0.mp4 | 3.000 | 3.000 | 3.000 |
| hHZvUeAdzeI.mp4 | 3.000 | 0.000 | 0.000 |
| qfUZBKDh9BY_processed.mp4 | 3.000 | 3.000 | 3.000 |
| YGSKW5AVBjc.mp4 | 3.000 | 0.000 | 0.000 |
| WCT6xM9jyzA.mp4 | 3.000 | 3.000 | 3.000 |
| PU7j9UF4lpA.mp4 | 1.000 | 1.000 | 1.000 |
| BY3nBVbUYjI.mp4 | 0.667 | 3.000 | 3.000 |
| 4Gb0lotHA8E.mp4 | 1.333 | 1.000 | 1.000 |
| S2nBBMbjS8w.mp4 | 3.000 | 3.000 | 3.000 |
| AkaEnPxMla8.mp4 | 1.667 | 3.000 | 3.000 |
| bRpUauseTVw.mp4 | 1.000 | 1.000 | 1.000 |
| q01PqUubacA.mp4 | 2.167 | 1.000 | 0.500 |
| EpFKDzmMnao_processed.mp4 | 3.000 | 3.000 | 2.333 |
| LEHR8YQNm_Q.mp4 | 0.333 | 0.000 | 0.000 |
| hq7nFVTFukc.mp4 | 3.000 | 3.000 | 1.000 |
| 68191uKawYw.mp4 | 3.000 | 3.000 | 3.000 |
| 5phZ6-eHbqM.mp4 | 2.667 | 2.667 | 2.000 |
| l1uE_pBqnvE.mp4 | 0.333 | 3.000 | 0.000 |
| tnMr9abBX7k.mp4 | 0.000 | 0.000 | 0.000 |
| ZNRSHr3b4uA.mp4 | 0.000 | 1.000 | 1.000 |
| 66XwG1CLHuU.mp4 | 2.667 | 3.000 | 3.000 |
| 9HsKNFr7xmI.mp4 | 1.833 | 3.000 | 3.000 |
| TseT4C38UAg.mp4 | 1.000 | 1.000 | 0.667 |
| uO8v6bjwRdo.mp4 | 2.000 | 0.000 | 0.000 |
| BfemWi1SKdw.mp4 | 2.000 | 0.000 | 0.000 |
| Zh3Yz3PiXZw_processed.mp4 | 2.667 | 2.667 | 3.000 |
| M7OiIun5NfQ.mp4 | 1.333 | 1.333 | 1.000 |
| X3COFNPpdDc_processed.mp4 | 0.667 | 0.667 | 0.667 |
| B363bRgVUUA_processed.mp4 | 0.667 | 1.000 | 1.000 |
| bTG65BRLaRE_processed.mp4 | 2.333 | 0.000 | 0.000 |
| lWCA_3GLrCE_processed.mp4 | 1.667 | 0.667 | 0.000 |
| T2XOiCM0OOA_processed.mp4 | 3.000 | 3.000 | 3.000 |
| cTA2rkKp6qo_processed.mp4 | 3.000 | 3.000 | 3.000 |
| ddzjFNvpZhM.mp4 | 3.000 | 3.000 | 3.000 |
| yVkdfJ9PkRQ.mp4 | 1.000 | 3.000 | 1.000 |
| 5eNhS0oaLHo_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 9j_HWkrSxzI_processed.mp4 | 3.000 | 3.000 | 3.000 |
| QkPJzK9SnTg.mp4 | 1.667 | 2.000 | 1.667 |
| Mwc4ePLjkQ8_processed.mp4 | 1.000 | 1.000 | 2.000 |
| WydM_QmW1ec.mp4 | 2.333 | 3.000 | 3.000 |
| vNhORnwcQcU_processed.mp4 | 3.000 | 3.000 | 1.667 |
| IFQ9zQekRio_processed.mp4 | 1.333 | 2.000 | 1.000 |
| L8luXQhnAGk.mp4 | 1.333 | 0.000 | 0.000 |
| zXR93P8EnxM_processed.mp4 | 1.000 | 1.333 | 1.667 |
| khXSmQHenSk_processed.mp4 | 3.000 | 0.000 | 0.000 |
| kiwy_nV-hxE.mp4 | 2.333 | 3.000 | 2.000 |
| b9DW-tHrQB8.mp4 | 2.667 | 3.000 | 3.000 |
| G4DPefY6-NM.mp4 | 1.667 | 2.333 | 2.333 |
| 0luoGkddtYw_processed.mp4 | 3.000 | 3.000 | 2.667 |
| HRe90ySP38U_processed.mp4 | 3.000 | 3.000 | 3.000 |
| 9-r4VLHQRlM_processed.mp4 | 1.667 | 2.000 | 2.000 |

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
- **MMBench-Video official (0-3)**: VLMEvalKit protocol replicated verbatim (semantic-similarity integer 0-3; multi-label `get_dimension_rating` aggregation with all/valid variants; judge failures → 0 in 'all', raw -1 kept in JSON). Judge model: `gpt-4-turbo` (official protocol uses gpt-4-turbo; swap via JUDGE_MODEL for paper numbers). Any run on fewer than the full 1,998 questions is a subset — NOT comparable to the official leaderboard
- Each method ran 3 independent trials; mean ± std reported over trials