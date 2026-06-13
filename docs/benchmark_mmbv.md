# Benchmark Results

> Video: `136 videos`  |  Benchmark: `benchmarks/mmbv_150.json`  |  Runs: 1  |  Generated: 2026-06-12 08:12

## Overall Accuracy

| Method | Acc · MMBench-Video official (0-3) | Avg Tool Calls | Avg Time (s) | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----------------|--------------|------|------|------|
| **vlm_direct** | 1.447 ± 0.000 | — | 6.2 | 6751 | — | 6751 |
| **rag_only** | 0.787 ± 0.000 | — | 3.1 | 984 | 11857 | 12842 |
| **agent_tiered** | 1.053 ± 0.000 | 0.5 | 7.1 | 4720 | 11622 | 16343 |
| **agent** | 1.193 ± 0.000 | 2.4 | 18.2 | 9724 | 11911 | 21636 |

## Per-Category Accuracy — MMBench-Video official (0-3)

| Category | vlm_direct | rag_only | agent_tiered | agent |
|----------|---------|---------|---------|---------|
| HL | 0.533±0.000 | 2.400±0.000 | 2.733±0.000 | 2.200±0.000 |
| CSR | 2.583±0.000 | 0.417±0.000 | 1.083±0.000 | 1.750±0.000 |
| FP-S | 1.440±0.000 | 0.760±0.000 | 0.760±0.000 | 1.040±0.000 |
| CP | 1.533±0.000 | 0.800±0.000 | 1.200±0.000 | 0.800±0.000 |
| LR | 1.500±0.000 | 0.100±0.000 | 0.900±0.000 | 0.500±0.000 |
| RR | 1.714±0.000 | 1.071±0.000 | 1.571±0.000 | 1.214±0.000 |
| TR | 1.333±0.000 | 0.167±0.000 | 0.300±0.000 | 0.833±0.000 |
| FP-C | 0.600±0.000 | 0.600±0.000 | 0.533±0.000 | 0.933±0.000 |
| AR | 2.214±0.000 | 1.143±0.000 | 1.357±0.000 | 1.857±0.000 |

## Per-Video Accuracy — MMBench-Video official (0-3)

| Video | vlm_direct | rag_only | agent_tiered | agent |
|-------|------|------|------|------|
| 4jOk3ajqJ2s_processed.mp4 | 3.000 | 3.000 | 3.000 | 3.000 |
| Qnyb73rf7gM_processed.mp4 | 0.000 | 1.000 | 3.000 | 3.000 |
| dSHcCllTCzY.mp4 | 3.000 | 0.000 | 1.000 | 1.000 |
| HtFrFZN8ud4.mp4 | 0.000 | 1.000 | 0.000 | 0.000 |
| Pfq9tqX_r-4.mp4 | 1.000 | 0.500 | 0.500 | 1.000 |
| bVceDFUlkX4.mp4 | 1.000 | 1.000 | 1.000 | 0.000 |
| a1ZNeTpMve8.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| cHazQV45SPs.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| ebFwtm1hUWM.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| DrQzaGncGmw.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| -9mIKCYg2vU.mp4 | 2.000 | 0.000 | 3.000 | 0.000 |
| u0GSFSvWDG4.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| Mylca_onT_I.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| YGE5Q2wgfs8.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| RWkKNcGmUI0.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| 115amzVdV44_processed.mp4 | 2.000 | 0.000 | 0.000 | 3.000 |
| umlonbnm1Kk.mp4 | 1.000 | 2.000 | 2.000 | 2.000 |
| zmHB11-V3cs.mp4 | 0.000 | 3.000 | 1.000 | 3.000 |
| zRRm1Kpx5zQ.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| rdQrwBVRzEg.mp4 | 2.000 | 0.000 | 0.000 | 0.000 |
| iBIGBcGo1rY.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| 3jQ_toeu314.mp4 | 1.667 | 0.000 | 0.667 | 1.333 |
| UIoqKfO8RJw.mp4 | 0.000 | 0.000 | 0.000 | 3.000 |
| z3yqHiQxlhg.mp4 | 1.000 | 0.000 | 0.000 | 0.500 |
| vBOWe1WK0Ig.mp4 | 1.000 | 0.000 | 0.000 | 1.000 |
| SX2Ajdf4-34.mp4 | 0.000 | 0.000 | 0.000 | 1.500 |
| d2ohLXJBykM.mp4 | 3.000 | 0.000 | 2.000 | 0.000 |
| mSaQXWoUHm0.mp4 | 1.000 | 0.000 | 1.000 | 0.000 |
| rQt4Q-ML7U4.mp4 | 2.000 | 2.000 | 2.000 | 1.000 |
| mfBNcc33EGA.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| BbARfF2Gf64.mp4 | 2.500 | 0.000 | 1.500 | 1.000 |
| py6OsO_WSqU.mp4 | 0.000 | 0.000 | 0.000 | 3.000 |
| SEdkof4g8Y8.mp4 | 1.000 | 1.000 | 2.000 | 1.000 |
| Eer_CfDgqhY.mp4 | 0.000 | 0.000 | 3.000 | 0.000 |
| 2Ja6H_up6TQ.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| opf_wezZTic.mp4 | 1.000 | 1.000 | 0.000 | 1.000 |
| tn3bGHxJH_M.mp4 | 0.000 | 0.000 | 0.000 | 1.000 |
| zm5bL2v876s.mp4 | 2.000 | 1.000 | 1.000 | 2.000 |
| RnDYM-EBsXM.mp4 | 3.000 | 1.000 | 3.000 | 3.000 |
| no9Ajy0tabs.mp4 | 3.000 | 2.000 | 0.000 | 0.000 |
| ccz1kfkdo2o.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| qyOpdQO2__c.mp4 | 0.000 | 1.000 | 0.000 | 0.000 |
| h70GdtAkEOw.mp4 | 0.000 | 3.000 | 3.000 | 0.000 |
| b5soe5g0igs.mp4 | 0.000 | 3.000 | 3.000 | 0.000 |
| nJYKKyZFqzU.mp4 | 3.000 | 3.000 | 0.000 | 0.000 |
| 3cs8S_urAXU.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| pod4x5NJoYI.mp4 | 3.000 | 3.000 | 3.000 | 0.000 |
| Mng2me2TNro.mp4 | 0.000 | 3.000 | 3.000 | 0.000 |
| jF31ICvl1T8.mp4 | 3.000 | 0.000 | 3.000 | 0.000 |
| QVzeW1_hyHI.mp4 | 0.000 | 2.000 | 0.000 | 3.000 |
| fYP4SryI9L0.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| _Zt1EuIEhvw_processed.mp4 | 0.000 | 0.000 | 0.000 | 1.000 |
| 2mYHGn_Pd5M_processed.mp4 | 1.000 | 0.000 | 2.000 | 3.000 |
| Q1cDKWToTGA.mp4 | 1.000 | 1.000 | 1.500 | 2.500 |
| 1zLgiOaOzNI.mp4 | 1.000 | 2.000 | 2.000 | 0.000 |
| bS1ePEZZCDY_processed.mp4 | 1.000 | 0.000 | 1.000 | 1.000 |
| 8dgyPRA86K0.mp4 | 3.000 | 3.000 | 3.000 | 3.000 |
| c_lFunATvhk.mp4 | 3.000 | 0.000 | 3.000 | 3.000 |
| RTSrYhD-Qk0.mp4 | 3.000 | 0.000 | 0.000 | 3.000 |
| dxE80fpImj8.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| V_Hn6pT4M-Y.mp4 | 3.000 | 2.000 | 3.000 | 3.000 |
| biAFfW-uiKI.mp4 | 1.000 | 0.000 | 1.000 | 0.000 |
| 0018ybk0K-E.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| 2zTwYcdW0Ew.mp4 | 0.000 | 0.000 | 1.000 | 0.000 |
| LOxxhecSHQM.mp4 | 0.000 | 0.000 | 0.500 | 0.000 |
| XnABXVhqXI0.mp4 | 3.000 | 3.000 | 2.000 | 3.000 |
| GgqhnkkJTp8.mp4 | 0.500 | 0.000 | 1.000 | 0.000 |
| 9uBbgltCs94.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| zON0wDD7VJY.mp4 | 0.000 | 0.000 | 0.000 | 2.000 |
| GhABIaANJCY.mp4 | 2.000 | 0.000 | 0.000 | 0.000 |
| Zvoxf_W1ZvA.mp4 | 2.000 | 1.000 | 1.000 | 0.000 |
| zBv_fuKyg5E.mp4 | 3.000 | 0.000 | 0.000 | 3.000 |
| O-17kqjsiFc_processed.mp4 | 3.000 | 0.000 | 3.000 | 3.000 |
| 9OxNk-d1PNw.mp4 | 0.000 | 0.000 | 0.000 | 1.000 |
| e_iZaS00xds.mp4 | 2.000 | 1.000 | 1.000 | 3.000 |
| ZVl-Lm_XaTI.mp4 | 3.000 | 3.000 | 3.000 | 3.000 |
| QH7GaLx5JYc.mp4 | 0.000 | 3.000 | 3.000 | 1.000 |
| xUkqUL5bXSE.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| HxxfnxOIzdo.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| rDWzQ6lZNpY.mp4 | 0.000 | 0.000 | 0.000 | 3.000 |
| QKHPOzA9Ge0_processed.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| rhkkCDTkcvI_processed.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| ApNRpFOKQrA.mp4 | 0.000 | 3.000 | 3.000 | 0.000 |
| W8OzZa16vtE.mp4 | 3.000 | 0.000 | 0.000 | 3.000 |
| r7COWvxlN5g_processed.mp4 | 3.000 | 0.000 | 0.000 | 3.000 |
| 0eKi5V1IOi0.mp4 | 3.000 | 2.000 | 2.000 | 3.000 |
| hHZvUeAdzeI.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| qfUZBKDh9BY_processed.mp4 | 3.000 | 0.000 | 3.000 | 0.000 |
| YGSKW5AVBjc.mp4 | 0.000 | 3.000 | 3.000 | 3.000 |
| WCT6xM9jyzA.mp4 | 2.000 | 3.000 | 3.000 | 3.000 |
| PU7j9UF4lpA.mp4 | 2.000 | 0.000 | 0.000 | 2.000 |
| BY3nBVbUYjI.mp4 | 3.000 | 1.000 | 1.000 | 1.000 |
| 4Gb0lotHA8E.mp4 | 2.000 | 0.000 | 0.000 | 0.000 |
| S2nBBMbjS8w.mp4 | 3.000 | 3.000 | 3.000 | 3.000 |
| AkaEnPxMla8.mp4 | 3.000 | 0.000 | 3.000 | 3.000 |
| bRpUauseTVw.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| q01PqUubacA.mp4 | 0.500 | 0.500 | 1.500 | 2.500 |
| EpFKDzmMnao_processed.mp4 | 2.000 | 1.000 | 2.000 | 1.000 |
| LEHR8YQNm_Q.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| hq7nFVTFukc.mp4 | 0.000 | 1.000 | 0.000 | 2.000 |
| 68191uKawYw.mp4 | 2.000 | 0.000 | 0.000 | 2.000 |
| 5phZ6-eHbqM.mp4 | 2.000 | 0.000 | 0.000 | 3.000 |
| l1uE_pBqnvE.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| tnMr9abBX7k.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| ZNRSHr3b4uA.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| 66XwG1CLHuU.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| 9HsKNFr7xmI.mp4 | 3.000 | 0.000 | 0.000 | 1.500 |
| TseT4C38UAg.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| uO8v6bjwRdo.mp4 | 0.000 | 0.000 | 0.000 | 1.000 |
| BfemWi1SKdw.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| Zh3Yz3PiXZw_processed.mp4 | 3.000 | 0.000 | 0.000 | 1.000 |
| M7OiIun5NfQ.mp4 | 1.000 | 0.000 | 1.000 | 2.000 |
| X3COFNPpdDc_processed.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| B363bRgVUUA_processed.mp4 | 1.000 | 0.000 | 1.000 | 0.000 |
| bTG65BRLaRE_processed.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| lWCA_3GLrCE_processed.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| T2XOiCM0OOA_processed.mp4 | 3.000 | 0.000 | 3.000 | 0.000 |
| cTA2rkKp6qo_processed.mp4 | 3.000 | 3.000 | 3.000 | 3.000 |
| ddzjFNvpZhM.mp4 | 3.000 | 3.000 | 2.000 | 2.000 |
| yVkdfJ9PkRQ.mp4 | 1.000 | 0.000 | 0.000 | 0.000 |
| 5eNhS0oaLHo_processed.mp4 | 3.000 | 1.500 | 1.000 | 1.500 |
| 9j_HWkrSxzI_processed.mp4 | 3.000 | 0.000 | 2.000 | 0.000 |
| QkPJzK9SnTg.mp4 | 1.000 | 0.000 | 0.000 | 3.000 |
| Mwc4ePLjkQ8_processed.mp4 | 3.000 | 1.000 | 0.000 | 0.000 |
| WydM_QmW1ec.mp4 | 3.000 | 0.000 | 1.000 | 1.000 |
| vNhORnwcQcU_processed.mp4 | 1.000 | 1.000 | 3.000 | 3.000 |
| IFQ9zQekRio_processed.mp4 | 1.000 | 3.000 | 2.000 | 3.000 |
| L8luXQhnAGk.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| zXR93P8EnxM_processed.mp4 | 2.000 | 0.000 | 1.000 | 0.000 |
| khXSmQHenSk_processed.mp4 | 0.000 | 0.000 | 0.000 | 0.000 |
| kiwy_nV-hxE.mp4 | 2.000 | 0.000 | 0.000 | 0.000 |
| b9DW-tHrQB8.mp4 | 3.000 | 0.000 | 0.000 | 0.000 |
| G4DPefY6-NM.mp4 | 2.500 | 2.500 | 2.500 | 1.500 |
| 0luoGkddtYw_processed.mp4 | 3.000 | 2.000 | 3.000 | 3.000 |
| HRe90ySP38U_processed.mp4 | 3.000 | 3.000 | 2.000 | 3.000 |
| 9-r4VLHQRlM_processed.mp4 | 2.000 | 3.000 | 2.000 | 3.000 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **agent_tiered**: Cost-aware agent — scene graph (or its summary, when >30 triplets) injected into context; the model decides at runtime whether to answer directly (one LLM call) or escalate to query/inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples N frames (default 4, see --vlm-frames), sends raw frames + question directly to VLM
- **Prebuild frame budget**: duration-adaptive — one frame per ~15s, clamped to [8, 24] (Charades-length clips stay at the historical 8)
- **Token accounting**: all counts are real API-reported `usage` summed over every call the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully counted; VL calls include image tokens in prompt_tokens). No estimates. **Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the one-time scene-graph build over that video's questions (vlm_direct has no prebuild). Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted
- **Break-even vs vlm_direct**: none — agent marginal cost (9724 tokens/Q) ≥ vlm_direct (6751 tokens/Q), so the 13138-token prebuild never pays back at this question volume
- **MMBench-Video official (0-3)**: VLMEvalKit protocol replicated verbatim (semantic-similarity integer 0-3, mean aggregation, judge failures → 0 per the official 'all' variant; raw -1 kept in JSON). Judge model: `qwen-max` (official protocol uses gpt-4-turbo; swap via JUDGE_MODEL for paper numbers)
- Each method ran 1 independent trials; mean ± std reported over trials