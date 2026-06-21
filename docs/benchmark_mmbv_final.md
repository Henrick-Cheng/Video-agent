# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 3  |  Generated: 2026-06-21 16:09

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Frames/Q | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|------|
| **agent_v2** | 1.984 ± 0.101 | 1.7 | 21.8 | 3.6 | 10546 | 6108 | 16655 |
| **vlm_transcript** | 1.727 ± 0.020 | — | 3.4 | 8.0 | 7299 | — | 7299 |
| **vlm_direct** | 1.478 ± 0.025 | — | 3.7 | 8.0 | 6748 | — | 6748 |

## Per-Category Accuracy — MMBench-Video official (0-3)

| Category | agent_v2 | vlm_transcript | vlm_direct |
|----------|---------|---------|---------|
| HL | 2.422±0.191 | 1.044±0.137 | 0.622±0.126 |
| CSR | 2.333±0.068 | 2.472±0.039 | 2.444±0.039 |
| FP-S | 2.040±0.182 | 1.667±0.038 | 1.427±0.019 |
| CP | 2.244±0.126 | 1.600±0.000 | 1.578±0.063 |
| LR | 2.200±0.245 | 1.900±0.000 | 1.567±0.047 |
| RR | 2.000±0.117 | 2.119±0.034 | 1.762±0.034 |
| TR | 1.544±0.150 | 1.767±0.094 | 1.367±0.027 |
| FP-C | 1.489±0.083 | 0.756±0.063 | 0.644±0.031 |
| AR | 2.143±0.101 | 2.500±0.000 | 2.333±0.034 |

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
- **MMBench-Video official (0-3)**: VLMEvalKit protocol replicated verbatim (semantic-similarity integer 0-3, mean aggregation, judge failures → 0 per the official 'all' variant; raw -1 kept in JSON). Judge model: `qwen-max` (official protocol uses gpt-4-turbo; swap via JUDGE_MODEL for paper numbers)
- Each method ran 3 independent trials; mean ± std reported over trials