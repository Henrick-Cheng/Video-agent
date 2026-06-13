# Benchmark Results

> Video: `10 videos`  |  Benchmark: `benchmarks/agqa_en_small.json`  |  Runs: 1  |  Generated: 2026-06-12 04:25

## Overall Accuracy

| Method | Acc · LLM-judge (0/0.5/1) | Acc · exact-match | Avg Tool Calls | Avg Time (s) | Tokens/Q (answer) | + Prebuild/Q | = Total/Q |
|--------|----|----|----------------|--------------|------|------|------|
| **agent** | 0.450 ± 0.000 | 0.429 ± 0.000 | 2.6 | 14.2 | 9315 | 971 | 10287 |
| **rag_only** | 0.343 ± 0.000 | 0.314 ± 0.000 | — | 1.6 | 953 | 980 | 1933 |
| **vlm_direct** | 0.371 ± 0.000 | 0.357 ± 0.000 | — | 2.7 | 626 | — | 626 |

## Per-Category Accuracy — LLM-judge (0/0.5/1)

| Category | agent | rag_only | vlm_direct |
|----------|---------|---------|---------|
| open | 0.381±0.000 | 0.286±0.000 | 0.357±0.000 |
| duration | 0.500±0.000 | 0.182±0.000 | 0.136±0.000 |
| binary | 0.625±0.000 | 0.625±0.000 | 0.542±0.000 |
| sequencing | 0.214±0.000 | 0.071±0.000 | 0.286±0.000 |

## Per-Category Accuracy — exact-match

| Category | agent | rag_only | vlm_direct |
|----------|---------|---------|---------|
| open | 0.381±0.000 | 0.238±0.000 | 0.333±0.000 |
| duration | 0.364±0.000 | 0.091±0.000 | 0.091±0.000 |
| binary | 0.625±0.000 | 0.625±0.000 | 0.542±0.000 |
| sequencing | 0.214±0.000 | 0.071±0.000 | 0.286±0.000 |

## Per-Video Accuracy — LLM-judge (0/0.5/1)

| Video | agent | rag_only | vlm_direct |
|-------|------|------|------|
| 03PRW.mp4 | 0.143 | 0.000 | 0.000 |
| 02DPI.mp4 | 0.429 | 0.000 | 0.143 |
| 07BSH.mp4 | 0.714 | 0.571 | 0.500 |
| 00607.mp4 | 0.714 | 0.571 | 0.429 |
| 06LBQ.mp4 | 0.571 | 0.286 | 0.714 |
| 00T1E.mp4 | 0.571 | 0.714 | 0.571 |
| 02SKC.mp4 | 0.571 | 0.357 | 0.571 |
| 07QNG.mp4 | 0.214 | 0.286 | 0.286 |
| 01THT.mp4 | 0.286 | 0.357 | 0.357 |
| 015XE.mp4 | 0.286 | 0.286 | 0.143 |

## Per-Video Accuracy — exact-match

| Video | agent | rag_only | vlm_direct |
|-------|------|------|------|
| 03PRW.mp4 | 0.143 | 0.000 | 0.000 |
| 02DPI.mp4 | 0.429 | 0.000 | 0.143 |
| 07BSH.mp4 | 0.714 | 0.571 | 0.571 |
| 00607.mp4 | 0.714 | 0.571 | 0.429 |
| 06LBQ.mp4 | 0.571 | 0.286 | 0.714 |
| 00T1E.mp4 | 0.571 | 0.714 | 0.571 |
| 02SKC.mp4 | 0.429 | 0.286 | 0.571 |
| 07QNG.mp4 | 0.143 | 0.286 | 0.286 |
| 01THT.mp4 | 0.286 | 0.143 | 0.143 |
| 015XE.mp4 | 0.286 | 0.286 | 0.143 |

## Notes

- **agent**: Full ReAct Agent — extracts frames, builds scene graph, uses query + inspect tools
- **rag_only**: Pre-builds full scene graph, then LLM answers from graph text only
- **vlm_direct**: Samples 4 frames, sends raw frames + question directly to VLM
- **Token accounting**: all counts are real API-reported `usage` summed over every call the method makes (agent: per-turn usage_metadata, so re-sent ReAct history is fully counted; VL calls include image tokens in prompt_tokens). No estimates. **Tokens/Q (answer)** is the marginal per-question cost; **+Prebuild/Q** amortizes the one-time scene-graph build over that video's questions (vlm_direct has no prebuild). Judge / short-answer-extraction calls are scoring infrastructure and are NOT counted
- **Break-even vs vlm_direct**: none — agent marginal cost (9315 tokens/Q) ≥ vlm_direct (626 tokens/Q), so the 6803-token prebuild never pays back at this question volume
- **LLM-judge**: `qwen-plus-latest` scores 0 / 0.5 / 1 against `key_facts` (partial credit; judge endpoint configurable via JUDGE_BASE_URL/JUDGE_MODEL/JUDGE_API_KEY)
- **exact-match**: strict normalized EM (1/0) against `_source.en_answer`; binary uses the first yes/no, others require normalized equality (length-guarded). Verbose answers (e.g. the ReAct agent) are reduced to their canonical short form by a deterministic extraction step before EM. NOTE: extraction is unreliable on open/'X or Y' questions (see docs/em_vs_agent_analysis.md) — treat non-binary EM as a conservative reference
- Each method ran 1 independent trials; mean ± std reported over trials